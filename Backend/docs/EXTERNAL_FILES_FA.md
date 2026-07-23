# نقشه یکپارچه‌سازی ماژول Attendance

ماژول attendance اکنون بخشی از Backend اصلی است و فایل «خارج از ماژول» برای نصب دستی وجود ندارد.
نقاط اتصال فعال عبارت‌اند از:

- `config/settings/base.py`: ثبت app، routeهای Celery، Beat و تنظیمات notification.
- `config/api_urls.py`: routeهای session، record، policy، alert، notification و report.
- `.env.example` و `.env.production.example`: محدودیت فایل، retry، alert و backendهای ارسال.
- `docker-compose.yml`: queue اعلان و Celery Beat.
- `tests/test_attendance.py`: workflowهای اصلی حضور و غیاب و رفتارهای تاریخ‌مند.
- migrationهای `attendance/0001` و `attendance/0002`.

مسیر canonical ماژول:

```text
Backend/hamamooz/apps/attendance
```

مسیر legacy زیر نباید وجود داشته باشد:

```text
Backend/apps/attendance
```
