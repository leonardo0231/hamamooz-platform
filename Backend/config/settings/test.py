from __future__ import annotations

import os

from .base import *  # noqa: F403

DEBUG = False
MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE  # noqa: F405
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

if (
    os.getenv(
        "REQUIRE_POSTGRES_TESTS",
        "false",
    ).lower()
    in {
        "1",
        "true",
        "yes",
    }
    and DATABASES["default"]["ENGINE"]
    != "django.db.backends.postgresql"
):
    raise RuntimeError(
        "This test run requires PostgreSQL."
    )

if os.getenv("TEST_USE_REDIS", "false").lower() not in {"1", "true", "yes"}:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
