# راهنمای استقرار سخت‌گیری‌شده

## اجرای محلی با فایل‌سیستم

در `.env` مقدار `USE_S3=false` باشد و اجرا کنید:

```bash
docker compose up --build
```

مسیر `/media/` توسط gateway از volume مشترک سرو می‌شود.

## اجرای S3/MinIO

در `.env` مقدار `USE_S3=true` و اطلاعات S3 را تنظیم کنید، سپس:

```bash
docker compose --profile s3 up --build
```

## Migration و static

Migration و `collectstatic` فقط در سرویس یک‌بارمصرف `release` اجرا می‌شوند. web، worker و beat پس از موفقیت release بالا می‌آیند؛ بنابراین replicaها هم‌زمان migration اجرا نمی‌کنند.

## TLS

در production باید TLS در load balancer بیرونی یا Nginx terminate شود. gateway مقدار `X-Forwarded-Proto` ورودی را حفظ می‌کند. بدون TLS واقعی، `SECURE_SSL_REDIRECT=true` فعال نشود. نمونه اولیه در `nginx/tls.conf.example` است.

## Redis

Cache و Celery broker جدا هستند. Redis broker با `noeviction` اجرا می‌شود تا پیام‌های صف بر اثر فشار cache حذف نشوند.

## Backup

`backup-db` از PostgreSQL، `backup-media` از volume محلی رسانه و `backup-storage` در profile `s3` از bucket نسخه می‌گیرد. volume محلی backup جایگزین نسخه off-host نیست؛ باید snapshot آن به مقصد رمزگذاری‌شده خارج از میزبان منتقل و restore drill دوره‌ای اجرا شود.

## پاک‌سازی فایل‌ها

ابتدا dry-run:

```bash
python manage.py purge_expired_files
```

سپس اجرای واقعی:

```bash
python manage.py purge_expired_files --apply
```
