from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.trace import get_trace_id


logger = logging.getLogger(__name__)


def _message_from_data(data: Any) -> str:
    if isinstance(data, dict):
        detail = data.get("detail")

        if detail:
            return str(detail)

    if isinstance(data, list) and data:
        return str(data[0])

    return "Request could not be processed."


def api_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response | None:
    response = exception_handler(
        exc,
        context,
    )

    if response is None:
        logger.error(
            "Unhandled API exception.",
            exc_info=(
                type(exc),
                exc,
                exc.__traceback__,
            ),
            extra={
                "view": str(context.get("view")),
            },
        )

        if settings.DEBUG:
            return None

        return Response(
            {
                "code": "internal_server_error",
                "message": (
                    "An unexpected error occurred."
                ),
                "details": {},
                "trace_id": get_trace_id(),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = "api_error"

    if isinstance(exc, ValidationError):
        code = "validation_error"

    elif isinstance(exc, APIException):
        code = str(exc.default_code)

    if (
        response.status_code
        == status.HTTP_401_UNAUTHORIZED
    ):
        code = "authentication_required"

    elif (
        response.status_code
        == status.HTTP_404_NOT_FOUND
    ):
        code = "not_found"

    original_data = response.data

    response.data = {
        "code": code,
        "message": _message_from_data(
            original_data
        ),
        "details": original_data,
        "trace_id": get_trace_id(),
    }

    return response