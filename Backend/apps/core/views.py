from __future__ import annotations

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.throttles import (
    ReadinessRateThrottle,
)


class HealthView(APIView):
    authentication_classes = ()

    permission_classes = (AllowAny,)

    throttle_classes = ()

    @extend_schema(
        responses={200: dict},
        auth=[],
    )
    def get(self, request: Request) -> Response:
        return Response(
            {
                "status": "ok",
                "service": "hamamooz-backend",
            }
        )


class ReadinessView(APIView):
    authentication_classes = ()

    permission_classes = (AllowAny,)

    throttle_classes = (
        ReadinessRateThrottle,
    )

    @extend_schema(
        responses={
            200: dict,
            503: dict,
        },
        auth=[],
    )
    def get(self, request: Request) -> Response:
        checks: dict[str, str] = {}

        ready = True

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            checks["database"] = "ok"

        except Exception:
            checks["database"] = "unavailable"
            ready = False

        try:
            probe_key = "readiness-probe"

            cache.set(
                probe_key,
                "ok",
                timeout=5,
            )

            cache_value = cache.get(probe_key)

            checks["cache"] = (
                "ok"
                if cache_value == "ok"
                else "unavailable"
            )

            ready = (
                ready
                and checks["cache"] == "ok"
            )

        except Exception:
            checks["cache"] = "unavailable"
            ready = False

        return Response(
            {
                "status": (
                    "ready"
                    if ready
                    else "not_ready"
                ),
                "checks": checks,
            },
            status=(
                status.HTTP_200_OK
                if ready
                else status.HTTP_503_SERVICE_UNAVAILABLE
            ),
        )