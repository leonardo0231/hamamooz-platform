# نمایه مستندات Backend

این فایل نقطه شروع مستندات Backend است. اسناد شماره‌دار فارسی، مستندات canonical این شاخه‌اند. فایل‌های انگلیسی قدیمی برای حفظ تاریخچه نگهداری می‌شوند، اما در صورت تعارض، کد جاری و اسناد شماره‌دار اولویت دارند.

## ترتیب منبع حقیقت

1. مدل‌ها، Serviceها، Viewها، Settings، Migrationها و Compose جاری
2. Schema زنده `/api/v1/schema/`
3. Schema تولیدشده با `./scripts/generate_openapi.sh build/openapi.yaml`
4. اسناد شماره‌دار فارسی این پوشه
5. اسناد legacy و artifactهای تاریخی

فایل‌های `openapi.yaml` و `docs/openapi-schema.yml` در شاخه فعلی artifact تاریخی‌اند. تا زمانی که از همان Commit دوباره تولید نشده باشند، برای تولید Client یا Contract test معتبر نیستند.

## نقشه مطالعه

| نیاز خواننده | سند |
|---|---|
| شناخت دامنه محصول | `01-MVP_SCOPE_FA.md` |
| شناخت معماری و وابستگی ماژول‌ها | `02-ARCHITECTURE_FA.md` |
| شناخت مدل‌ها، قیود و state machineها | `03-DATA_MODEL_FA.md` |
| اتصال Frontend یا Client | `04-API_FA.md` و Schema زنده |
| طراحی دسترسی و امنیت | `05-SECURITY_FA.md` و `permissions-matrix.md` |
| استقرار و نگهداری | `06-OPERATIONS_FA.md` و `13-RUNBOOK_FA.md` |
| تست و CI | `07-TESTING_FA.md` |
| چرایی تصمیم‌ها | `08-DECISIONS_FA.md` و `decisions/` |
| انتقال آفلاین Imageها | `09-OFFLINE_DEPLOYMENT_FA.md` |
| کنترل بسته تحویلی | `10-DELIVERY_MANIFEST_FA.md` |
| تنظیم `.env` | `11-CONFIGURATION_FA.md` |
| توسعه قابلیت جدید | `12-DEVELOPMENT_FA.md` |
| نتیجه بازبینی فنی | `14-BACKEND_REVIEW_FA.md` |
| جزئیات Attendance | `ARCHITECTURE_FA.md` و `API_REFERENCE_FA.md` |

## قواعد نگهداری

- هر Endpoint جدید باید هم‌زمان در View، تست، Schema تولیدشده و `04-API_FA.md` دیده شود.
- هر متغیر محیطی جدید باید در `.env.example` یا `.env.production.example` و `11-CONFIGURATION_FA.md` ثبت شود.
- هر state machine یا constraint جدید باید در `03-DATA_MODEL_FA.md` و تست مربوط ثبت شود.
- هر تغییر استقرار باید `docker-compose.yml`، `06-OPERATIONS_FA.md` و `09-OFFLINE_DEPLOYMENT_FA.md` را هم‌زمان به‌روزرسانی کند.
- نتیجه تست ثابت داخل متن نگهداری نمی‌شود؛ CI همان Commit منبع نتیجه است.
- گزارش‌های تاریخی مانند `FIX_REPORT_*.md` و `VALIDATION_REPORT_FA.md` با تاریخ خود خوانده می‌شوند و جای وضعیت جاری را نمی‌گیرند.

## کنترل پیشنهادی در CI

```bash
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest --cov=hamamooz --cov-report=term-missing --cov-report=xml
python manage.py spectacular --api-version v1 --file build/openapi.yaml --validate
git diff --exit-code -- build/openapi.yaml
```

برای جلوگیری از اختلاف مستندات و کد، بهتر است یک Job جدا مسیرهای تولیدشده OpenAPI و فهرست متغیرهای محیطی را با اسناد مقایسه کند.
