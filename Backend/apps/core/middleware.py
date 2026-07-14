from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Callable

from django.http import (
    HttpRequest,
    HttpResponse,
)

from apps.core.trace import set_trace_id


logger = logging.getLogger(
    "hamamooz.requests"
)


TRACE_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9._:-]{1,64}$"
)


class TraceIdMiddleware:
    header_name = "HTTP_X_REQUEST_ID"

    def __init__(
        self,
        get_response: Callable[
            [HttpRequest],
            HttpResponse,
        ],
    ) -> None:
        self.get_response = get_response

    def __call__(
        self,
        request: HttpRequest,
    ) -> HttpResponse:
        supplied = request.META.get(
            self.header_name,
            "",
        ).strip()

        if (
            supplied
            and TRACE_ID_PATTERN.fullmatch(
                supplied
            )
        ):
            trace_id = supplied
        else:
            trace_id = str(uuid.uuid4())

        request.trace_id = trace_id  # type: ignore[attr-defined]

        set_trace_id(trace_id)

        response = self.get_response(request)

        response["X-Request-ID"] = trace_id

        return response


class RequestLoggingMiddleware:
    def __init__(
        self,
        get_response: Callable[
            [HttpRequest],
            HttpResponse,
        ],
    ) -> None:
        self.get_response = get_response

    def __call__(
        self,
        request: HttpRequest,
    ) -> HttpResponse:
        started_at = time.monotonic()

        try:
            response = self.get_response(
                request
            )
        except Exception:
            logger.exception(
                "request.failed",
                extra=self._context(
                    request,
                    started_at=started_at,
                    status_code=500,
                    outcome="error",
                ),
            )

            raise

        outcome = (
            "success"
            if response.status_code < 400
            else "failure"
        )

        level = (
            logging.INFO
            if response.status_code < 500
            else logging.ERROR
        )

        logger.log(
            level,
            "request.completed",
            extra=self._context(
                request,
                started_at=started_at,
                status_code=(
                    response.status_code
                ),
                outcome=outcome,
            ),
        )

        return response

    @staticmethod
    def _context(
        request: HttpRequest,
        *,
        started_at: float,
        status_code: int,
        outcome: str,
    ) -> dict:
        resolver_match = (
            request.resolver_match
        )

        route = (
            resolver_match.route
            if resolver_match is not None
            else None
        )

        user = getattr(
            request,
            "user",
            None,
        )

        user_id = (
            getattr(user, "pk", None)
            if getattr(
                user,
                "is_authenticated",
                False,
            )
            else None
        )

        return {
            "user_id": user_id,
            "method": request.method,
            "path": request.path,
            "route": route,
            "status_code": status_code,
            "duration_ms": round(
                (
                    time.monotonic()
                    - started_at
                )
                * 1000,
                2,
            ),
            "outcome": outcome,
        }