# راهبرد و نتیجه تست

## نتیجه تحویل

```text
64 passed, 1 PostgreSQL-only concurrency test
Ruff: passed
Django system check: passed
Migration drift check: passed
OpenAPI validation: passed with zero warning/error
Dependency audit: no known vulnerabilities
Coverage: 83.07% branch-aware
```

## حوزه‌های تست‌شده

| فایل | سناریوها |
|---|---|
| `test_access.py` | دبیر فقط ارائه خودش، منع شعبه غیرمجاز، منع Assessment دبیر دیگر، عدم افشای کاربران، منع حذف فیزیکی کاربر |
| `test_auth.py` | ورود JWT و ایجاد Audit |
| `test_scores_and_calculations.py` | ثبت گروهی، ارسال ناقص، رد، تأیید/قفل، اصلاح قفل، تاریخچه، وزن، رتبه، غیبت |
| `test_imports.py` | Import معتبر، Rollback کامل در یک ردیف نامعتبر و تبدیل XLSX خراب به Job ناموفق |
| `test_reports_and_enrollment.py` | PDF واقعی و آرشیو Snapshot، الزام Lock برای خروجی رسمی، انتقال و تاریخچه مبدأ/مقصد |
| `test_security_regressions.py` | هدر حوزه، Cross-tenant write، سلسله‌مراتب نقش، Audit تغییر و قیود nullable |
| `test_enrollment_invariants.py` | ظرفیت، تاریخ، انتقال رفت‌وبرگشت و رقابت هم‌زمان PostgreSQL |
| `test_api_workflows.py` | جریان کامل حساب، ارزیابی، Import، گزارش، ولی و ثبت‌نام در سطح API |
| `test_reports_dashboard_core.py` | گزارش انتقال تاریخی، confinement رسانه، Query dashboard و health |
| `test_management_and_tasks.py` | Seed idempotent و Taskهای محاسبه/گزارش |

## اجرای محلی

```bash
pytest
pytest --cov=hamamooz --cov-report=term-missing
```

Settings تست از SQLite، Cache حافظه، Storage محلی، Password hasher سریع و Celery eager استفاده
می‌کند. CI علاوه بر تست، PostgreSQL 17 و Redis را بالا می‌آورد، Migration و OpenAPI را Validate
می‌کند، dependency audit انجام می‌دهد، MinIO خصوصی/versioned را smoke-test می‌کند و یک Dump را
در دیتابیس جدا Restore می‌کند.

## تست‌های ضروری قبل از Production

- Load test روی سخت‌افزار واقعی ۴ vCPU/۸ GB
- Restore drill دوره‌ای روی Host جدا (CI بازیابی دیتابیس ایزوله را انجام می‌دهد)
- تست S3/MinIO با فایل‌های بزرگ و URL امضاشده (CI اتصال و versioning را smoke-test می‌کند)
- تست مرورگر روی PDF فارسی با لوگوهای واقعی
- تست نفوذ مستقل RBAC/Object ID (ممیزی خودکار وابستگی‌ها در CI فعال است)
- سناریوی قطع Redis حین Queue و Retry
- PostgreSQL lock/concurrency در ثبت نمره گروهی هم‌زمان (ظرفیت ثبت‌نام در CI پوشش دارد)

Coverage عدد تضمین کیفیت کامل نیست؛ بخش‌های حساس Domain با اولویت پوشش داده شده‌اند. Gate فعلی
۷۸٪ و پوشش واقعی ۸۳٫۰۷٪ branch-aware است.
