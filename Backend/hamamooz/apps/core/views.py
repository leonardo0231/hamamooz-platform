import logging
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connection
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from redis import Redis
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class LiveHealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response({"status": "ok", "service": "hamamooz-api"})


class ReadyHealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT})
    def get(self, request):
        checks = {"database": False, "cache": False, "broker": False, "storage": False}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                checks["database"] = cursor.fetchone()[0] == 1
        except Exception:
            logger.exception("readiness_database_failed")
        try:
            key = f"health-ready:{uuid4()}"
            cache.set(key, "ok", 5)
            checks["cache"] = cache.get(key) == "ok"
            cache.delete(key)
        except Exception:
            logger.exception("readiness_cache_failed")
        if settings.READINESS_CHECK_BROKER:
            try:
                client = Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2)
                checks["broker"] = bool(client.ping())
                client.close()
            except Exception:
                logger.exception("readiness_broker_failed")
        else:
            checks["broker"] = True
        if settings.READINESS_CHECK_STORAGE:
            try:
                name = default_storage.save(f"health/.ready-{uuid4()}.txt", ContentFile(b"ok"))
                checks["storage"] = default_storage.exists(name)
                default_storage.delete(name)
            except Exception:
                logger.exception("readiness_storage_failed")
        else:
            checks["storage"] = True
        status_code = 200 if all(checks.values()) else 503
        return Response(
            {
                "status": "ready" if status_code == 200 else "not_ready",
                **checks,
                "checks": checks,
            },
            status=status_code,
        )
