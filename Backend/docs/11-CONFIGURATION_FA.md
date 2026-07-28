# مرجع پیکربندی و متغیرهای محیطی

Settings پایه از Environment خوانده می‌شود. `.env.example` برای توسعه و `.env.production.example` برای Production baseline هستند. Secret واقعی هرگز Commit نمی‌شود.

## Django و شبکه

| متغیر | پیش‌فرض | Production | توضیح |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | development در نمونه | `config.settings.production` | انتخاب Settings |
| `DJANGO_SECRET_KEY` | unsafe development | الزامی، حداقل ۵۰ نویسه | امضای Django/JWT |
| `DJANGO_DEBUG` | false در base | false | Debug |
| `DJANGO_ALLOWED_HOSTS` | localhost | الزامی، بدون `*` | Host header |
| `DJANGO_CORS_ALLOWED_ORIGINS` | خالی | دامنه Frontend | CORS |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | خالی | originهای HTTPS | CSRF trusted origins |
| `SECURE_SSL_REDIRECT` | true در production | true با TLS واقعی | redirect HTTPS |
| `SECURE_HSTS_SECONDS` | 31536000 | پس از اطمینان TLS | HSTS |
| `TRUST_X_FORWARDED_FOR` | false | فقط پشت proxy قابل اعتماد | IP client در Audit |

## Database

| متغیر | مثال | توضیح |
|---|---|---|
| `POSTGRES_DB` | `hamamooz` | ساخت container DB |
| `POSTGRES_USER` | `hamamooz` | کاربر DB |
| `POSTGRES_PASSWORD` | secret | رمز container DB |
| `DATABASE_URL` | `postgresql://...` | تنظیم Django DB؛ Production فقط PostgreSQL |

Query parameter `sslmode` از DATABASE_URL به psycopg منتقل می‌شود.

## Redis و Celery

| متغیر | پیش‌فرض منطقی | توضیح |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Cache |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Result backend |
| `CELERY_TASK_ALWAYS_EAGER` | false | اجرای synchronous در تست/توسعه |

Compose از دو Redis جدا استفاده می‌کند: `redis-cache` و `redis-broker`.

## JWT

| متغیر | پیش‌فرض | توضیح |
|---|---:|---|
| `JWT_ACCESS_MINUTES` | 15 | عمر Access token |
| `JWT_REFRESH_DAYS` | 7 | عمر Refresh token |

Refresh rotation و blacklist همیشه فعال‌اند.

## Storage

| متغیر | پیش‌فرض | توضیح |
|---|---|---|
| `USE_S3` | false | FileSystem یا S3 |
| `AWS_ACCESS_KEY_ID` | خالی/نمونه | access key |
| `AWS_SECRET_ACCESS_KEY` | خالی/نمونه | secret key |
| `AWS_STORAGE_BUCKET_NAME` | `hamamooz-private` | bucket |
| `AWS_S3_ENDPOINT_URL` | خالی | MinIO/S3 endpoint |
| `AWS_S3_REGION_NAME` | `us-east-1` | region |
| `AWS_S3_ADDRESSING_STYLE` | `path` | path/virtual host |
| `AWS_QUERYSTRING_AUTH` | true | signed URL |

در Production با `USE_S3=true`، credential placeholder startup را fail می‌کند.

## Attendance

| متغیر | پیش‌فرض | توضیح |
|---|---:|---|
| `ATTENDANCE_MAX_EVIDENCE_SIZE` | 5 MiB | سقف هر مدرک |
| `ATTENDANCE_MAX_EVIDENCE_TOTAL_SIZE` | 10 MiB | سقف مجموع مدارک درخواست |
| `ATTENDANCE_ASYNC_NOTIFICATIONS` | true | ارسال از Celery |
| `ATTENDANCE_AUTO_ALERTS_ENABLED` | true | ارزیابی خودکار |
| `ATTENDANCE_ALERT_HOUR` | 16 | ساعت Beat به وقت `Asia/Tehran` |
| `ATTENDANCE_ALERT_MINUTE` | 0 | دقیقه Beat |
| `ATTENDANCE_SMS_BACKEND` | Disabled backend | کلاس Backend پیامک |
| `ATTENDANCE_NOTIFICATION_MAX_ATTEMPTS` | 5 | سقف تلاش |
| `ATTENDANCE_NOTIFICATION_STALE_MINUTES` | 15 | بازیابی claim منقضی |

Backend SMS باید interface مورد انتظار `attendance.notifications` را پیاده‌سازی کند. کانال `in_app` تا وجود پنل والد `skipped` می‌شود.

## Import و Report

| متغیر | پیش‌فرض | توضیح |
|---|---:|---|
| `IMPORT_PROCESSING_TIMEOUT_MINUTES` | 30 | تشخیص Job stale |
| `REPORT_PROCESSING_TIMEOUT_MINUTES` | 30 | تشخیص Report stale |
| `IMPORT_MAX_ROWS` | 5000 | سقف ردیف Workbook |
| `IMPORT_MAX_COLUMNS` | 20 | سقف ستون |
| `IMPORT_MAX_UNCOMPRESSED_BYTES` | 50 MiB | سقف محتوای unzip شده |

## Email

| متغیر | پیش‌فرض | توضیح |
|---|---|---|
| `EMAIL_BACKEND` | SMTP backend | کلاس Backend ایمیل |
| `EMAIL_HOST` | خالی | در Production SMTP الزامی |
| `EMAIL_PORT` | 587 | پورت |
| `EMAIL_HOST_USER` | خالی | username |
| `EMAIL_HOST_PASSWORD` | خالی | password |
| `EMAIL_USE_TLS` | true | STARTTLS |
| `EMAIL_TIMEOUT` | 10 | ثانیه |
| `DEFAULT_FROM_EMAIL` | `noreply@hamamooz.local` | فرستنده |

برای محیطی که ایمیل ندارد، Backend مناسب non-SMTP را صریح تنظیم کنید؛ در غیر این صورت Production بدون `EMAIL_HOST` بالا نمی‌آید.

## Log و Sentry

| متغیر | پیش‌فرض | توضیح |
|---|---:|---|
| `LOG_LEVEL` | INFO | سطح root logger |
| `SENTRY_DSN` | خالی | فعال‌سازی Sentry |
| `SENTRY_ENVIRONMENT` | `unknown` | نام محیط |
| `SENTRY_TRACES_SAMPLE_RATE` | 0.05 | نرخ trace |

PII پیش‌فرض به Sentry ارسال نمی‌شود.

## Backup و Retention

| متغیر | پیش‌فرض | توضیح |
|---|---:|---|
| `BACKUP_INTERVAL_SECONDS` | 86400 | فاصله backup loop |
| `BACKUP_RETENTION_DAYS` | 14 | نگهداری backup محلی |
| `IMPORT_FILE_RETENTION_DAYS` | 90 | فایل Import |
| `REPORT_FILE_RETENTION_DAYS` | 365 | PDF گزارش |
| `EVIDENCE_FILE_RETENTION_DAYS` | 730 | مدارک غیبت |

## متغیرهای عملیاتی command

- `SEED_ADMIN_PASSWORD`: جایگزین امن آرگومان `--admin-password`
- `BACKUP_DIR`: مقصد اسکریپت backup
- `MEDIA_SOURCE_DIR`: منبع backup رسانه
- `MEDIA_TARGET_DIR`: مقصد restore رسانه
- `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`: ابزارهای PostgreSQL

## تولید Secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

پس از تغییر JWT signing key، tokenهای قبلی نامعتبر می‌شوند و rollout باید آگاهانه انجام شود.
