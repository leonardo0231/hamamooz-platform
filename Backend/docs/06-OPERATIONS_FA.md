# استقرار و عملیات

## سرویس‌های Compose

| سرویس | نقش | همیشه فعال |
|---|---|---:|
| `release` | Migration و collectstatic یک‌بارمصرف | بله |
| `web` | Gunicorn + Django API | بله |
| `gateway` | Nginx، static و media محلی | بله |
| `worker` | Celery queueها | بله |
| `beat` | Scheduler هشدار Attendance | بله |
| `db` | PostgreSQL 17 | بله |
| `redis-cache` | Cache با `allkeys-lru` | بله |
| `redis-broker` | Broker/Result با AOF و `noeviction` | بله |
| `minio`, `minio-init` | Object storage خصوصی | فقط profile `s3` |
| `backup-db` | pg_dump دوره‌ای | بله |
| `backup-media` | archive رسانه محلی | بله |
| `backup-storage` | mirror bucket | فقط profile `s3` |

Web با ۳ Worker و ۲ Thread و Celery با concurrency=2 شروع می‌شود. این اعداد baseline هستند و باید با Load test مقصد تنظیم شوند.

## راه‌اندازی

FileSystem محلی:

```bash
cp .env.example .env
# USE_S3=false
docker compose up --build -d
```

MinIO/S3 profile:

```bash
# USE_S3=true و AWS_* کامل
docker compose --profile s3 up --build -d
```

وضعیت:

```bash
docker compose ps
docker compose logs -f release web worker beat gateway
curl -fsS http://localhost:8000/api/v1/health/live/
curl -fsS http://localhost:8000/api/v1/health/ready/
```

## Migration و Release

`entrypoint.sh` فقط command را اجرا می‌کند و Migration داخل web/worker نیست. سرویس `release` قبل از سایر سرویس‌های برنامه این دو دستور را اجرا می‌کند:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

برای استقرار orchestrated، همین رفتار باید به Job یک‌بارمصرف منتقل شود. اجرای هم‌زمان Migration در چند Replica ممنوع است.

## Queueها و Scheduler

Worker Queueهای زیر را مصرف می‌کند:

```text
default, imports, reports, calculations, notifications
```

Beat فقط `evaluate-attendance-alerts-daily` را بر اساس ساعت و دقیقه تنظیم‌شده اجرا می‌کند. این عملیات باید جداگانه Schedule شوند:

```bash
python manage.py dispatch_attendance_notifications --limit 100
python manage.py purge_expired_files --apply
```

برای آن‌ها CronJob، systemd timer یا scheduler پلتفرم تعریف کنید.

## Health

- Liveness فقط زنده بودن Process را بررسی می‌کند.
- Readiness اتصال DB و Cache را بررسی می‌کند؛ Storage در تنظیم پایه فعال است.
- Production بررسی Broker و Storage را اجباری می‌کند.
- شکست readiness باید ترافیک را از Replica خارج کند، نه اینکه Container را الزاماً restart کند.

## بکاپ

### دیتابیس

`backup-db` هر `BACKUP_INTERVAL_SECONDS` یک dump فرمت custom و SHA-256 می‌سازد و فایل‌های قدیمی‌تر از `BACKUP_RETENTION_DAYS` را حذف می‌کند.

```bash
docker compose exec backup-db /scripts/backup_postgres.sh
```

### رسانه محلی

`backup-media` از volume رسانه archive فشرده و checksum می‌سازد.

### S3/MinIO

`backup-storage` bucket را در مسیر timestampدار mirror می‌کند. Versioning bucket فعال است، اما mirror محلی جای off-host backup را نمی‌گیرد.

### بازیابی دیتابیس

روی محیط آزمایشی یا Change Window:

```bash
export PGHOST=...
export PGDATABASE=...
export PGUSER=...
export PGPASSWORD=...
./scripts/restore_postgres.sh /path/hamamooz_TIMESTAMP.dump
```

اسکریپت checksum را در صورت وجود کنترل و سپس `pg_restore --clean --if-exists` اجرا می‌کند؛ داده فعلی مقصد تغییر می‌کند.

### بازیابی رسانه

```bash
export MEDIA_TARGET_DIR=/media
./scripts/restore_media.sh /path/hamamooz_media_TIMESTAMP.tar.gz
```

Restore drill باید دوره‌ای اجرا و RPO/RTO واقعی ثبت شود.

## Retention فایل

| نوع | متغیر پیش‌فرض |
|---|---:|
| Import source | `IMPORT_FILE_RETENTION_DAYS=90` |
| Report PDF | `REPORT_FILE_RETENTION_DAYS=365` |
| Attendance evidence | `EVIDENCE_FILE_RETENTION_DAYS=730` |

ابتدا dry-run:

```bash
python manage.py purge_expired_files
```

سپس:

```bash
python manage.py purge_expired_files --apply
```

## مانیتورینگ

حداقل alertها:

- نرخ 5xx و 429
- latency p50/p95/p99
- readiness failure
- Queue depth و oldest message age
- task retry/failure/dead-letter
- زمان Import و PDF
- Connection و slow query PostgreSQL
- فضای DB، backup volume و object storage
- عمر آخرین backup موفق
- تعداد Assessment ناقص و Attendance session نهایی‌نشده

JSON log شامل timestamp، level، logger، message و Request ID است. Metrics exporter در MVP وجود ندارد و باید در زیرساخت افزوده شود.

## Production checklist

```text
[ ] DJANGO_SETTINGS_MODULE=config.settings.production
[ ] Secretها و passwordهای نمونه جایگزین شده‌اند
[ ] ALLOWED_HOSTS/CORS/CSRF محدود هستند
[ ] TLS واقعی فعال و SECURE_SSL_REDIRECT=true است
[ ] DB/Redis/MinIO مستقیم منتشر نشده‌اند
[ ] SMTP/SMS/S3 واقعی و تست‌شده‌اند
[ ] release job فقط یک‌بار اجرا می‌شود
[ ] backup off-host و رمزگذاری‌شده است
[ ] restore drill موفق ثبت شده است
[ ] scheduler پاک‌سازی و notification recovery فعال است
[ ] OpenAPI از همان Commit تولید و validate شده است
[ ] تست‌ها روی PostgreSQL موفق‌اند
```
