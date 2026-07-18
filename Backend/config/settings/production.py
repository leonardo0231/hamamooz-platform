from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

weak_markers = {"change-me", "replace-with", "unsafe-development"}

if len(SECRET_KEY) < 50 or any(marker in SECRET_KEY.lower() for marker in weak_markers):  # noqa: F405
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be a unique production secret with at least 50 characters"
    )

if not os.getenv("DJANGO_ALLOWED_HOSTS") or "*" in ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must explicitly list production hosts and cannot contain '*'"
    )

database = DATABASES["default"]  # noqa: F405
if database["ENGINE"] == "django.db.backends.postgresql":
    password = database.get("PASSWORD", "")
    if not password or any(marker in password.lower() for marker in weak_markers):
        raise ImproperlyConfigured("DATABASE_URL must contain a non-placeholder password")

if USE_S3:  # noqa: F405
    s3_credentials = [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]  # noqa: F405
    if any(
        not value or any(marker in value.lower() for marker in weak_markers)
        for value in s3_credentials
    ):
        raise ImproperlyConfigured("Production S3 credentials must be configured")

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"
