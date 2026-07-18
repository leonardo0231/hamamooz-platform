# استقرار و عملیات

## سرویس‌ها

| سرویس | نقش |
|---|---|
| `web` | Gunicorn + Django API |
| `worker` | Celery برای Import، PDF و محاسبات |
| `db` | PostgreSQL 17 |
| `redis` | Broker، Result backend و Cache |
| `minio` | Object Storage خصوصی |
| `minio-init` | ساخت Bucket، فعال‌سازی Versioning و بستن Anonymous access |
| `backup` | اجرای دوره‌ای pg_dump و Retention |

Compose فعلی برای سرور ۴ vCPU و ۸ GB RAM محافظه‌کارانه تنظیم شده است: Web با ۳ Worker و ۲ Thread، Celery با concurrency=2 و Redis با سقف ۵۱۲ MB. قبل از تغییر این اعداد، Load Test انجام شود.

## Production checklist

```text
[ ] DJANGO_SETTINGS_MODULE=config.settings.production
[ ] DJANGO_SECRET_KEY تصادفی و خارج از Git
[ ] تمام passwordهای نمونه تغییر کرده‌اند
[ ] ALLOWED_HOSTS/CORS/CSRF محدود شده‌اند
[ ] TLS فعال و SECURE_SSL_REDIRECT=true
[ ] MinIO و PostgreSQL پورت عمومی ندارند
[ ] SENTRY_DSN یا سامانه مانیتورینگ تنظیم شده
[ ] بکاپ خارج Host کپی می‌شود
[ ] Restore روی محیط جدا تست شده
[ ] seed_demo با Credential موقت اجرا/مدیر تغییر داده شده
[ ] OpenAPI و تست‌ها در CI موفق‌اند
[ ] `.env.production.example` مبنا بوده و تمام placeholderها جایگزین شده‌اند
```

## Migration

Entry point قبل از Start وب `migrate --noinput` و `collectstatic` را اجرا می‌کند. برای استقرار چند Instance، Migration باید به Job جداگانه Deployment منتقل شود تا هم‌زمان روی چند Container اجرا نشود.

## بکاپ

سرویس `backup` هر `BACKUP_INTERVAL_SECONDS` ثانیه یک Custom-format dump و SHA-256 می‌سازد و فایل‌های قدیمی‌تر از `BACKUP_RETENTION_DAYS` را حذف می‌کند.

اجرای دستی:

```bash
docker compose exec backup /scripts/backup_postgres.sh
```

نمایش Volume بکاپ:

```bash
docker volume inspect hamamooz-mvp_backup_data
```

Restore باید روی DB خالی/آزمایشی انجام شود:

```bash
export PGHOST=...
export PGDATABASE=...
export PGUSER=...
export PGPASSWORD=...
./scripts/restore_postgres.sh /path/hamamooz_YYYYMMDDTHHMMSSZ.dump
```

اسکریپت در صورت وجود فایل checksum آن را قبل از Restore کنترل می‌کند. اجرای Restore روی Production داده فعلی را Clean می‌کند و باید در Change Window انجام شود.

## مانیتورینگ

- `/health/live/`: فقط زنده‌بودن Process
- `/health/ready/`: اتصال DB و Cache؛ در شکست HTTP 503
- JSON log: timestamp، level، logger، message و Request ID
- Sentry اختیاری و بدون `send_default_pii`
- Celery worker healthcheck با `inspect ping`

شاخص‌های پیشنهادی برای مرحله بعد: latency p95، نرخ 5xx، Queue depth، زمان PDF، زمان Import، تعداد Connection DB، Slow query و درصد Assessmentهای ناقص.

## مقیاس و Performance

- Pagination تا سقف ۲۰۰ رکورد از بار حافظه جلوگیری می‌کند.
- Indexهای ترکیبی روی Enrollment، Assessment، Score، Result و Audit قرار دارند.
- Queryهای پرتکرار `select_related/prefetch_related` دارند.
- گزارش و Import در Worker انجام می‌شوند.
- در ۲ تا ۴ هزار دانش‌آموز نیازی به Microservice یا Read replica نیست.

تست خودکار Import تعداد ۲۰۰۰ دانش‌آموز را پوشش می‌دهد و CI رقابت هم‌زمان روی آخرین ظرفیت
کلاس را با قفل سطری PostgreSQL بررسی می‌کند. برای Load Test کامل هنوز باید سناریوی ۱۳ شعبه،
ثبت نمره هم‌زمان دبیران، گزارش گروهی و Import روی سخت‌افزار مقصد اجرا شود.
