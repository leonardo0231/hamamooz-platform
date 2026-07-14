from __future__ import annotations

import hashlib

from rest_framework.throttling import (
    AnonRateThrottle,
    SimpleRateThrottle,
)

from apps.accounts.security import canonicalize_email


class LoginIPRateThrottle(AnonRateThrottle):
    scope = "login_ip"


class LoginIdentifierRateThrottle(SimpleRateThrottle):
    scope = "login_identifier"

    def get_cache_key(self, request, view) -> str | None:
        raw_email = request.data.get("email")

        if not isinstance(raw_email, str):
            return None

        canonical = canonicalize_email(raw_email)

        if not canonical:
            return None

        identifier = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        return self.cache_format % {
            "scope": self.scope,
            "ident": identifier,
        }


class ReadinessRateThrottle(AnonRateThrottle):
    scope = "readiness"