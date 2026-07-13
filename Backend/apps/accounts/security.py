from __future__ import annotations

import hashlib
import ipaddress
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.request import Request
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from apps.accounts.models import (
    LoginAttempt,
    User,
)


def canonicalize_email(email: str) -> str:
    return User.objects.normalize_email(email)


def hash_login_identifier(email: str) -> str:
    canonical = canonicalize_email(email)

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def _parse_ip(value: str | None) -> str | None:
    if not value:
        return None

    try:
        return str(
            ipaddress.ip_address(
                value.strip()
            )
        )
    except ValueError:
        return None


def get_request_ip(
    request: Request | None,
) -> str | None:
    if request is None:
        return None

    proxy_count = int(
        getattr(
            settings,
            "TRUSTED_PROXY_COUNT",
            0,
        )
    )

    if proxy_count <= 0:
        return _parse_ip(
            request.META.get("REMOTE_ADDR")
        )

    forwarded = request.META.get(
        "HTTP_X_FORWARDED_FOR",
        "",
    )

    addresses = [
        item.strip()
        for item in forwarded.split(",")
        if item.strip()
    ]

    if len(addresses) < proxy_count:
        return None

    candidate = addresses[-proxy_count]

    return _parse_ip(candidate)


def is_login_locked(email: str) -> bool:
    identifier_hash = hash_login_identifier(
        email
    )

    window_start = (
        timezone.now()
        - timedelta(
            seconds=(
                settings
                .LOGIN_FAILURE_WINDOW_SECONDS
            )
        )
    )

    last_success_at = (
        LoginAttempt.objects
        .filter(
            identifier_hash=identifier_hash,
            succeeded=True,
        )
        .order_by("-created_at")
        .values_list(
            "created_at",
            flat=True,
        )
        .first()
    )

    if (
        last_success_at is not None
        and last_success_at > window_start
    ):
        window_start = last_success_at

    failures = LoginAttempt.objects.filter(
        identifier_hash=identifier_hash,
        succeeded=False,
        created_at__gte=window_start,
    ).count()

    return (
        failures
        >= settings.LOGIN_FAILURE_LIMIT
    )


def record_login_attempt(
    *,
    email: str,
    request: Request | None,
    succeeded: bool,
    user: User | None = None,
) -> LoginAttempt:
    return LoginAttempt.objects.create(
        identifier_hash=(
            hash_login_identifier(email)
        ),
        ip_address=get_request_ip(request),
        succeeded=succeeded,
        user=user if succeeded else None,
    )


@transaction.atomic
def change_password_and_revoke_sessions(
    *,
    user: User,
    new_password: str,
) -> None:
    user.set_password(new_password)

    user.save(
        update_fields=("password",)
    )

    outstanding_tokens = (
        OutstandingToken.objects
        .filter(
            user=user,
            expires_at__gt=timezone.now(),
        )
        .iterator()
    )

    for token in outstanding_tokens:
        BlacklistedToken.objects.get_or_create(
            token=token
        )