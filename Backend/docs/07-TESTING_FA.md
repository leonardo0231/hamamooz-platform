# راهبرد و نتیجه تست

## نتیجه تحویل

```text
17 passed
Ruff: passed
Django system check: passed
Migration drift check: passed
OpenAPI validation: passed with zero warning/error
Coverage: 63.39%
```

## حوزه‌های تست‌شده

| فایل | سناریوها |
|---|---|
| `test_access.py` | دبیر فقط ارائه خودش، منع شعبه غیرمجاز، منع Assessment دبیر دیگر، عدم افشای کاربران، منع حذف فیزیکی کاربر |
| `test_auth.py` | ورود JWT و ایجاد Audit |
| `test_scores_and_calculations.py` | ثبت گروهی، ارسال ناقص، رد، تأیید/قفل، اصلاح قفل، تاریخچه، وزن، رتبه، غیبت |
| `test_imports.py` | Import معتبر، Rollback کامل در یک ردیف نامعتبر و تبدیل XLSX خراب به Job ناموفق |
| `test_reports_and_enrollment.py` | PDF واقعی و آرشیو Snapshot، الزام Lock برای خروجی رسمی، انتقال و تاریخچه مبدأ/مقصد |

## اجرای محلی

```bash
pytest
pytest --cov=hamamooz --cov-report=term-missing
```

Settings تست از SQLite، Cache حافظه، Storage محلی، Password hasher سریع و Celery eager استفاده می‌کند. CI علاوه بر تست، PostgreSQL 17 و Redis را بالا می‌آورد، Migration واقعی را اجرا و OpenAPI را Validate می‌کند.

## تست‌های ضروری قبل از Production

- Load test روی سخت‌افزار واقعی ۴ vCPU/۸ GB
- Restore drill از بکاپ روی Host جدا
- تست S3/MinIO با فایل‌های بزرگ و URL امضاشده
- تست مرورگر روی PDF فارسی با لوگوهای واقعی
- Security scan وابستگی‌ها و تست نفوذ RBAC/Object ID
- سناریوی قطع Redis حین Queue و Retry
- PostgreSQL lock/concurrency در ثبت نمره گروهی هم‌زمان

Coverage عدد تضمین کیفیت کامل نیست؛ بخش‌های حساس Domain با اولویت پوشش داده شده‌اند. Gate فعلی ۵۰٪ است و پوشش واقعی تحویل ۶۳٫۳۹٪ است. برای نسخه پیشرفته Gate باید تدریجی به ۷۵٪ یا بیشتر برسد.
