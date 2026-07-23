import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parents[2]


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


def database_config(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme == "sqlite":
        name = unquote(parsed.path)
        if name in {"/:memory:", ":memory:"}:
            name = ":memory:"
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": name}
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must use sqlite://, postgres:// or postgresql://")
    query = parse_qs(parsed.query)
    options = {}
    if query.get("sslmode"):
        options["sslmode"] = query["sslmode"][0]
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "localhost",
        "PORT": parsed.port or 5432,
        "CONN_MAX_AGE": 60,
        "OPTIONS": options,
    }


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key-change-before-production")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "storages",
    "hamamooz.apps.core",
    "hamamooz.apps.organizations",
    "hamamooz.apps.accounts",
    "hamamooz.apps.students",
    "hamamooz.apps.academics",
    "hamamooz.apps.imports",
    "hamamooz.apps.reports",
    "hamamooz.apps.dashboard",
    "hamamooz.apps.attendance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "hamamooz.apps.core.middleware.RequestIDMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": database_config(os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"))
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True
DATE_FORMAT = "Y-m-d"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_S3 = env_bool("USE_S3", False)
if USE_S3:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "hamamooz-private")
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")
    AWS_S3_ADDRESSING_STYLE = os.getenv("AWS_S3_ADDRESSING_STYLE", "path")
    AWS_QUERYSTRING_AUTH = env_bool("AWS_QUERYSTRING_AUTH", True)
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
CORS_ALLOW_CREDENTIALS = False
TRUST_X_FORWARDED_FOR = env_bool("TRUST_X_FORWARDED_FOR", False)
READINESS_CHECK_BROKER = env_bool("READINESS_CHECK_BROKER", False)
READINESS_CHECK_STORAGE = env_bool("READINESS_CHECK_STORAGE", True)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "hamamooz.apps.core.pagination.StandardPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "hamamooz.apps.core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "1200/hour", "login": "10/min"},
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "HamAmoz School Platform API",
    "DESCRIPTION": "API نسخه MVP سامانه چندشعبه‌ای هم‌آموز",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [{"jwtAuth": []}],
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,
    }
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 15 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 14 * 60
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ROUTES = {
    "hamamooz.apps.imports.tasks.*": {"queue": "imports"},
    "hamamooz.apps.reports.tasks.*": {"queue": "reports"},
    "hamamooz.apps.academics.tasks.*": {"queue": "calculations"},
    "hamamooz.apps.attendance.tasks.dispatch_parent_notification": {"queue": "notifications"},
    "hamamooz.apps.attendance.tasks.evaluate_attendance_alerts": {"queue": "calculations"},
}
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = True

ATTENDANCE_MAX_EVIDENCE_SIZE = int(os.getenv("ATTENDANCE_MAX_EVIDENCE_SIZE", str(5 * 1024 * 1024)))
ATTENDANCE_MAX_EVIDENCE_TOTAL_SIZE = int(
    os.getenv("ATTENDANCE_MAX_EVIDENCE_TOTAL_SIZE", str(10 * 1024 * 1024))
)
ATTENDANCE_ASYNC_NOTIFICATIONS = env_bool("ATTENDANCE_ASYNC_NOTIFICATIONS", True)
ATTENDANCE_AUTO_ALERTS_ENABLED = env_bool("ATTENDANCE_AUTO_ALERTS_ENABLED", True)
ATTENDANCE_SMS_BACKEND = os.getenv(
    "ATTENDANCE_SMS_BACKEND",
    "hamamooz.apps.attendance.notifications.DisabledSMSBackend",
)
ATTENDANCE_ALERT_HOUR = int(os.getenv("ATTENDANCE_ALERT_HOUR", "16"))
ATTENDANCE_ALERT_MINUTE = int(os.getenv("ATTENDANCE_ALERT_MINUTE", "0"))
ATTENDANCE_NOTIFICATION_MAX_ATTEMPTS = int(os.getenv("ATTENDANCE_NOTIFICATION_MAX_ATTEMPTS", "5"))
ATTENDANCE_NOTIFICATION_STALE_MINUTES = int(
    os.getenv("ATTENDANCE_NOTIFICATION_STALE_MINUTES", "15")
)
REPORT_PROCESSING_TIMEOUT_MINUTES = int(os.getenv("REPORT_PROCESSING_TIMEOUT_MINUTES", "30"))
IMPORT_PROCESSING_TIMEOUT_MINUTES = int(os.getenv("IMPORT_PROCESSING_TIMEOUT_MINUTES", "30"))
IMPORT_MAX_ROWS = int(os.getenv("IMPORT_MAX_ROWS", "5000"))
IMPORT_MAX_COLUMNS = int(os.getenv("IMPORT_MAX_COLUMNS", "20"))
IMPORT_MAX_UNCOMPRESSED_BYTES = int(
    os.getenv("IMPORT_MAX_UNCOMPRESSED_BYTES", str(50 * 1024 * 1024))
)
IMPORT_FILE_RETENTION_DAYS = int(os.getenv("IMPORT_FILE_RETENTION_DAYS", "90"))
REPORT_FILE_RETENTION_DAYS = int(os.getenv("REPORT_FILE_RETENTION_DAYS", "365"))
EVIDENCE_FILE_RETENTION_DAYS = int(os.getenv("EVIDENCE_FILE_RETENTION_DAYS", "730"))

CELERY_BEAT_SCHEDULE = {
    "evaluate-attendance-alerts-daily": {
        "task": "hamamooz.apps.attendance.tasks.evaluate_attendance_alerts",
        "schedule": crontab(hour=ATTENDANCE_ALERT_HOUR, minute=ATTENDANCE_ALERT_MINUTE),
    }
}

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@hamamooz.local")


FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "hamamooz.apps.core.logging.JSONFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.db.backends": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        send_default_pii=False,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
        environment=os.getenv("SENTRY_ENVIRONMENT", "unknown"),
    )
