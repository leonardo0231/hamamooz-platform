from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from apps.core.trace import get_trace_id


SENSITIVE_PATTERN = re.compile(
    r"(?i)"
    r"(authorization|password|access|refresh|token)"
    r"([\"']?\s*[:=]\s*[\"']?)"
    r"([^,\s\"']+)"
)


class SensitiveDataFilter(logging.Filter):
    def filter(
        self,
        record: logging.LogRecord,
    ) -> bool:
        message = record.getMessage()

        record.msg = SENSITIVE_PATTERN.sub(
            r"\1\2[REDACTED]",
            message,
        )

        record.args = ()

        return True


class RequestContextFilter(logging.Filter):
    def filter(
        self,
        record: logging.LogRecord,
    ) -> bool:
        record.trace_id = get_trace_id()

        defaults: dict[str, Any] = {
            "user_id": None,
            "method": None,
            "path": None,
            "route": None,
            "status_code": None,
            "duration_ms": None,
            "outcome": None,
        }

        for key, value in defaults.items():
            if not hasattr(record, key):
                setattr(record, key, value)

        return True


class JsonFormatter(logging.Formatter):
    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(
                UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": record.trace_id,
        }

        optional_fields = (
            "user_id",
            "method",
            "path",
            "route",
            "status_code",
            "duration_ms",
            "outcome",
        )

        for field in optional_fields:
            value = getattr(
                record,
                field,
                None,
            )

            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = (
                self.formatException(
                    record.exc_info
                )
            )

        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        )