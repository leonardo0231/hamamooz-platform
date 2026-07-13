from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


DEBUG = False


PLACEHOLDER_SECRETS = {
    "",
    "hamamooz",
    "change-me-in-each-environment",
    "replace-with-a-strong-secret",
    "unsafe-development-only-secret",
}


def require_strong_secret(
    name: str,
    value: str,
    *,
    minimum_length: int,
) -> None:
    if (
        value in PLACEHOLDER_SECRETS
        or len(value) < minimum_length
    ):
        raise ImproperlyConfigured(
            f"{name} must be configured with a "
            f"non-placeholder value of at least "
            f"{minimum_length} characters."
        )


if (
    os.environ.get("DJANGO_SETTINGS_MODULE")
    != "config.settings.production"
):
    raise ImproperlyConfigured(
        "Production must use "
        "config.settings.production."
    )


require_strong_secret(
    "DJANGO_SECRET_KEY",
    SECRET_KEY,  # noqa: F405
    minimum_length=50,
)

require_strong_secret(
    "JWT_SIGNING_KEY",
    JWT_SIGNING_KEY,  # noqa: F405
    minimum_length=32,
)


if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must contain explicit "
        "production hostnames."
    )


if env.bool("USE_S3", default=False):  # noqa: F405
    require_strong_secret(
        "AWS_SECRET_ACCESS_KEY",
        AWS_SECRET_ACCESS_KEY,  # noqa: F405
        minimum_length=24,
    )


SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SAMESITE = "Lax"

SECURE_HSTS_SECONDS = 31536000

SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_HSTS_PRELOAD = True

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"