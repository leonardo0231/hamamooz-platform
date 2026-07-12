from __future__ import annotations

import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.trace import set_trace_id


class TraceIdMiddleware:
    header_name = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        supplied = request.META.get(self.header_name, "").strip()
        trace_id = supplied[:128] if supplied else str(uuid.uuid4())
        request.trace_id = trace_id  # type: ignore[attr-defined]
        set_trace_id(trace_id)
        response = self.get_response(request)
        response["X-Request-ID"] = trace_id
        return response
