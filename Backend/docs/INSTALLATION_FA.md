# راهنمای نصب ماژول حضور و غیاب هم‌آموز

## مبنای پیاده‌سازی

این بسته برای شاخه `backend/mvp-bootstrap` و مسیر فعال بک‌اند نوشته شده است:

```text
Backend/hamamooz/apps/
```

پوشه قدیمی `Backend/apps/` در این پیاده‌سازی استفاده نشده است. هیچ فایل Frontend یا GitHub Actions تغییر نمی‌کند.

## فایل‌های تحویلی

1. `hamamooz-attendance-module.zip` فقط app جدید را دارد و از ریشه مخزن در مسیر زیر باز می‌شود:

```text
Backend/hamamooz/apps/attendance/
```

2. `hamamooz-attendance-external-changes.zip` فقط تغییرات خارج از app را دارد:

```text
Backend/config/settings/base.py.patch
Backend/config/api_urls.py.patch
Backend/.env.example.patch
Backend/docker-compose.yml.patch
Backend/tests/test_attendance_api.py
```

3. `hamamooz-attendance-complete-package.zip` شامل هر دو بسته، مستندات و manifest است.

## نصب مرحله‌به‌مرحله

از ریشه مخزن و روی شاخه بک‌اند اجرا کنید:

```bash
git switch backend/mvp-bootstrap
unzip hamamooz-attendance-module.zip
unzip hamamooz-attendance-external-changes.zip -d attendance-external
```

سپس patchها را از ریشه مخزن اعمال کنید:

```bash
git apply attendance-external/Backend/config/settings/base.py.patch
git apply attendance-external/Backend/config/api_urls.py.patch
git apply attendance-external/Backend/.env.example.patch
git apply attendance-external/Backend/docker-compose.yml.patch
cp attendance-external/Backend/tests/test_attendance_api.py Backend/tests/test_attendance_api.py
```

قبل از اعمال، می‌توانید سازگاری patchها را بدون تغییر فایل‌ها بررسی کنید:

```bash
git apply --check attendance-external/Backend/config/settings/base.py.patch
git apply --check attendance-external/Backend/config/api_urls.py.patch
git apply --check attendance-external/Backend/.env.example.patch
git apply --check attendance-external/Backend/docker-compose.yml.patch
```

اگر فایل‌های پروژه بعداً تغییر کرده‌اند و patch اعمال نشد، محتوای هر patch دقیقاً مشخص می‌کند کدام import، app، router، queue و متغیر محیطی باید اضافه شود؛ کل فایل فعلی را با فایل دیگری جایگزین نکنید.

## migration و بررسی پروژه

```bash
cd Backend
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py check
pytest tests/test_attendance_api.py -q
ruff check hamamooz/apps/attendance tests/test_attendance_api.py
```

در Docker:

```bash
cd Backend
docker compose build web worker beat
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py check
docker compose run --rm web pytest tests/test_attendance_api.py -q
docker compose up -d
```

## تنظیمات محیطی

مقادیر پیشنهادی در `.env.example.patch` آمده‌اند:

```dotenv
ATTENDANCE_MAX_EVIDENCE_SIZE=5242880
ATTENDANCE_ASYNC_NOTIFICATIONS=true
ATTENDANCE_AUTO_ALERTS_ENABLED=true
ATTENDANCE_ALERT_HOUR=16
ATTENDANCE_ALERT_MINUTE=0
ATTENDANCE_SMS_BACKEND=hamamooz.apps.attendance.notifications.DisabledSMSBackend
```

برای ایمیل، اطلاعات SMTP را نیز تکمیل کنید:

```dotenv
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=noreply@example.com
```

## پیامک

پروژه provider پیامک مشخصی نداشت؛ بنابراین backend پیش‌فرض پیامک عمداً غیرفعال است و تلاش برای SMS به‌صورت `FAILED` ثبت می‌شود. برای اتصال سرویس واقعی، یک کلاس مشتق از `BaseSMSBackend` بسازید و مسیر import آن را در `ATTENDANCE_SMS_BACKEND` قرار دهید. نمونه قرارداد:

```python
from hamamooz.apps.attendance.notifications import BaseSMSBackend


class ProviderSMSBackend(BaseSMSBackend):
    def send(self, *, recipient, message, metadata=None):
        # فراخوانی SDK/API ارائه‌دهنده و بررسی پاسخ
        return True
```

```dotenv
ATTENDANCE_SMS_BACKEND=your_package.sms.ProviderSMSBackend
```

## زمان‌بندی هشدارها

patch تنظیمات یک Celery Beat schedule روزانه می‌سازد و patch Docker سرویس `beat` و queue اعلان‌ها را اضافه می‌کند. اجرای دستی جایگزین:

```bash
python manage.py evaluate_attendance_alerts
python manage.py dispatch_attendance_notifications --limit 100
```

## نکات استقرار

- مدارک غیبت با storage پیش‌فرض پروژه ذخیره می‌شوند؛ در production همان MinIO/S3 پروژه استفاده خواهد شد.
- حداکثر اندازه پیش‌فرض مدرک ۵ مگابایت است و فقط PDF، JPG/JPEG، PNG و WEBP با بررسی signature پذیرفته می‌شوند.
- غیبت موجه مستقیماً از bulk/correction قابل ثبت نیست و فقط پس از workflow تأیید مسئول ایجاد می‌شود.
- همه queryهای API با `X-School-ID` و `X-Organization-ID` و RBAC موجود پروژه scope می‌شوند.
- برای ثبت گروهی، جلسه باید `draft` باشد. نهایی‌سازی فقط وقتی انجام می‌شود که تمام ثبت‌نام‌های فعال کلاس رکورد داشته باشند.
