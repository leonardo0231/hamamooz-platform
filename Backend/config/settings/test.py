from .base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
<<<<<<< HEAD
=======

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

>>>>>>> d1ab717a752428a109c9478b838e8338dccd9265
CELERY_TASK_ALWAYS_EAGER = True
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_ROOT = BASE_DIR / ".test-media"  # noqa: F405
