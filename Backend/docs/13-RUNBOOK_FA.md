# Runbook عملیات Backend

## API پاسخ نمی‌دهد

1. وضعیت Containerها:

```bash
docker compose ps
docker compose logs --tail=200 gateway web release
```

2. Health مستقیم web و از gateway را مقایسه کنید.
3. خطای `release` را برای Migration/collectstatic بررسی کنید.
4. اتصال DB و Redis را کنترل کنید.
5. Request ID گزارش‌شده توسط Client را در JSON log جست‌وجو کنید.

Restart بدون شناخت علت، آخرین اقدام است:

```bash
docker compose restart web gateway
```

## Readiness برابر 503 است

- DB: `pg_isready` و connection limit
- Cache: `redis-cli -h redis-cache ping`
- Broker در Production: `redis-cli -h redis-broker ping`
- Storage: credential، bucket و endpoint
- DNS/Network بین Containerها

Liveness موفق و Readiness ناموفق یعنی Process زنده است ولی نباید ترافیک بگیرد.

## Worker backlog یا Task fail

```bash
docker compose logs --tail=300 worker
docker compose exec worker celery -A config inspect ping
docker compose exec worker celery -A config inspect active
docker compose exec worker celery -A config inspect reserved
```

Queueهای مورد انتظار: `imports`, `reports`, `calculations`, `notifications`, `default`.

- Import/Report processing قدیمی از Endpoint retry قابل بازیابی است.
- Notification failed از action retry یا command dispatch قابل صف‌بندی است.
- قبل از retry انبوه، سرویس خارجی و علت failure را رفع کنید.

## اعلان والدین ارسال نمی‌شود

1. `EMAIL_BACKEND`, `EMAIL_HOST` یا `ATTENDANCE_SMS_BACKEND` را بررسی کنید.
2. وضعیت ParentNotification، attempts، next attempt و error را ببینید.
3. Worker queue `notifications` را بررسی کنید.
4. command بازیابی:

```bash
python manage.py dispatch_attendance_notifications --limit 100
```

`in_app` در MVP عمداً `skipped` است. Disabled SMS backend ارسال واقعی انجام نمی‌دهد.

## Import در processing مانده

- timeout پیش‌فرض ۳۰ دقیقه است.
- فایل و checksum را بررسی کنید.
- فضای storage و memory Worker را کنترل کنید.
- Job stale را از `POST /imports/{id}/retry/` تکرار کنید.
- قبل از retry، از عدم اجرای Worker قبلی مطمئن شوید؛ claim دیتابیس از duplicate جلوگیری می‌کند ولی بار اضافی مطلوب نیست.

## Report تولید نمی‌شود

- همه Assessmentهای فعال باید `locked` باشند.
- Resultها و CalculationPolicy مربوط را بررسی کنید.
- WeasyPrint/Pango داخل Image را تست کنید:

```bash
docker compose exec web python -c \
  "from weasyprint import HTML; print(HTML(string='<p>ok</p>').write_pdf()[:4])"
```

- فضای media/S3 و permission فایل را بررسی کنید.
- Report stale/failed را پس از رفع علت دوباره ایجاد کنید.

## Migration شکست خورده

1. web/worker جدید را بالا نیاورید.
2. log کامل `release` را ذخیره کنید.
3. Backup قبل از rollout را تأیید کنید.
4. Migration head و schema فعلی را مقایسه کنید.
5. rollback فقط در صورت migration reversible/backward-compatible انجام شود.
6. در غیر این صورت restore روی محیط جدا و تصمیم Change Management لازم است.

اجرای دستی:

```bash
docker compose run --rm release
```

## ظرفیت کلاس یا Lock contention

- Transactionهای طولانی و queryهای waiting در PostgreSQL را بررسی کنید.
- bulk operationها را کوچک‌تر کنید.
- از retry کور Client جلوگیری کنید.
- اگر deadlock تکرار شد، ترتیب lock در Service باید بازبینی شود.

## فضای دیسک کم است

```bash
docker system df
docker volume ls
docker compose exec db df -h
docker compose exec backup-db du -sh /backups/*
```

- retention backup را فقط پس از اطمینان از نسخه off-host کاهش دهید.
- `purge_expired_files` را ابتدا dry-run اجرا کنید.
- log و Imageهای بی‌استفاده را با سیاست زیرساخت پاک کنید.

## Backup و Restore drill

حداقل ماهانه:

1. جدیدترین dump و checksum را انتخاب کنید.
2. DB آزمایشی خالی بسازید.
3. `restore_postgres.sh` را اجرا کنید.
4. Migration status، تعداد رکوردهای کلیدی و smoke test را کنترل کنید.
5. رسانه یا bucket مرتبط را restore کنید.
6. زمان واقعی را به‌عنوان RTO و فاصله داده را به‌عنوان RPO ثبت کنید.

## Incident evidence

برای هر Incident نگه دارید:

```text
زمان شروع/پایان و timezone
Commit SHA و Image digest
Request IDها
logهای web/worker/gateway/release
DB/Redis/Storage health
تغییرات اخیر env/migration
اقدام mitigation
ریشه مشکل و اقدام پیشگیرانه
```

Secret، token و داده شخصی را قبل از اشتراک log حذف کنید.
