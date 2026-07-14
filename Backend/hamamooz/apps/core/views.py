from django.core.cache import cache
from django.db import connection
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


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
        checks = {"database": False, "cache": False}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                checks["database"] = cursor.fetchone()[0] == 1
        except Exception:
            pass
        try:
            cache.set("health-ready", "ok", 5)
            checks["cache"] = cache.get("health-ready") == "ok"
        except Exception:
            pass
        status_code = 200 if all(checks.values()) else 503
        return Response(
            {"status": "ready" if status_code == 200 else "not_ready", **checks}, status=status_code
        )
