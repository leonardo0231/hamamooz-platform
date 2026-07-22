# فایل‌های خارج از ماژول که باید تغییر کنند

## الزامی

### `Backend/config/settings/base.py`

- افزودن `hamamooz.apps.attendance` به `INSTALLED_APPS`.
- route کردن task اعلان‌ها و هشدارها.
- تنظیم اندازه مدرک، async notification، SMS backend و زمان هشدار.
- Celery Beat schedule.
- تنظیمات SMTP ایمیل.

### `Backend/config/api_urls.py`

- import شش ViewSet ماژول.
- ثبت شش route در `DefaultRouter`.

## الزامی برای deployment Docker

### `Backend/docker-compose.yml`

- افزودن queue `notifications` به worker.
- افزودن سرویس Celery Beat برای محاسبه خودکار هشدارها.

## پیکربندی

### `Backend/.env.example`

- متغیرهای attendance و SMTP.

## تست جدید

### `Backend/tests/test_attendance_api.py`

- تست API، workflow، گزارش، alert، tenant scope، evidence و notification.

## فایل‌هایی که نیاز به تغییر ندارند

- `Backend/config/celery.py`: از قبل `autodiscover_tasks()` دارد.
- `Backend/hamamooz/apps/core/tenancy.py`: مدل‌ها propertyهای `school_id` و `organization_id` لازم را ارائه می‌کنند.
- `Backend/pyproject.toml`: dependency جدیدی اضافه نشده است.
- تمام Frontend.
- تمام GitHub Actions/workflows.
