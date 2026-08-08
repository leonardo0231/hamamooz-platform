# HamAmoz Platform

سامانه‌ی مدیریت آموزشی چندشعبه‌ای **هم‌آموز (HamAmoz)** برای مدیریت ساختار مدرسه، کاربران و دسترسی‌ها، دانش‌آموزان و ثبت‌نام، برنامه درسی، ارزیابی و نمره، حضور و غیاب، کارنامه، ورود اطلاعات از Excel، اعلان‌ها، داشبورد و عملیات Audit.

این Branch یک Snapshot مستنداتی از وضعیت جاری پروژه است و در تاریخ **2026-08-08** با آخرین تغییرات `backend/comprehensive-manual-hardening` / PR `#4` همگام شده است. تغییرات PR #4 هنوز در زمان این Snapshot به `backend/hardening` Merge نشده‌اند؛ بنابراین برای بررسی رفتار جدید، کد همان Feature Branch و قرارداد موجود در این Branch مبنا هستند.

## وضعیت Snapshot

| مورد | مقدار |
|---|---|
| Feature branch مبنا | `backend/comprehensive-manual-hardening` |
| PR | `#4 - feat: harden comprehensive import and simplify manual data entry` |
| Head بررسی‌شده | `c30d0a57d1d05c77b295797dae4e652295174e4e` |
| Base PR | `backend/hardening` |
| Backend CI | PASS |
| Backend tests | `137 passed` |
| Backend coverage | `80.08%` با حداقل موردنیاز `78%` |
| Frontend CI | PASS |
| Frontend tests | `21 passed` |
| OpenAPI validation | PASS / `0 errors` |
| Generated frontend catalog | `173 operations`, `170 schemas` |

## Source of Truth

در صورت اختلاف مستندات، قرارداد یا برداشت‌ها، ترتیب مرجع پروژه به شکل زیر است:

1. کد جاری Backend و Frontend
2. Testها و Migrationها
3. Schema زنده/تولیدشده OpenAPI
4. `contracts/openapi.yaml`
5. مستندات معماری و تصمیم‌ها
6. README و مستندات راهنما
7. فرضیات

فایل `contracts/openapi.yaml` خروجی تولیدشده است و **نباید دستی ویرایش شود**.

## معماری

HamAmoz یک **Modular Monolith** است. مرزبندی Domainها حفظ می‌شود، اما تا زمانی که نیاز عملیاتی واقعی وجود نداشته باشد سیستم به Microservice شکسته نمی‌شود.

```text
Browser
  -> Frontend / Nginx
      -> /api proxy
          -> Django REST API / Gunicorn
              -> PostgreSQL
              -> Redis
              -> Celery Worker / Celery Beat
              -> S3-compatible storage when enabled
              -> WeasyPrint reports
              -> Sentry when configured
```

ساختار Monorepo اصلی:

```text
Backend/       Django REST API, Celery, migrations, tests
Frontend/      TypeScript browser application
contracts/     Generated OpenAPI contract and API changelog
docs/          Shared architecture/integration documentation
.github/       CI workflows and repository automation
docker-compose.yml
```

## Stack

### Backend

- Python 3.12+
- Django 5.x
- Django REST Framework
- PostgreSQL
- Redis
- Celery + Celery Beat
- SimpleJWT
- django-filter
- drf-spectacular / OpenAPI
- S3-compatible private storage when enabled
- WeasyPrint
- Gunicorn
- Sentry when configured

### Frontend

- TypeScript
- esbuild-based build flow
- generated API contract/catalog workflow
- Nginx in production
- central API client and endpoint registry

## Domainهای اصلی

- Organization و School/Branch
- Academic Year، Term، Grade Level و Class Section
- User، Role و scoped permission
- Student، Guardian و Enrollment
- Subject، Grade Subject، Course Offering و Teacher Assignment
- Assessment، Score و Calculation Policy
- Monthly Evaluation با ۷۴ شاخص
- Attendance Policy، Session و Record
- Report Card، reports و analytics
- XLSX imports
- Notifications
- Dashboard
- Audit و operational workflows

## Multi-Tenant و Scope Safety

امنیت Scope یکی از اصول اصلی پروژه است. هر Query و Mutation باید Organization، School، Class/Course، Teacher Scope، User Role و Object Permission را در Backend اعمال کند. Frontend صرفاً ابزار UX است و فیلتر Frontend هیچ‌وقت مرز امنیتی محسوب نمی‌شود.

ریسک‌های زیر Critical هستند:

- IDOR
- Tenant escape
- Cross-school / cross-branch data leakage
- Privilege escalation
- نوشتن داده در Scope اشتباه

Roleهای فعلی:

- `system_admin`
- `organization_admin`
- `school_manager`
- `educational_deputy`
- `operator`
- `teacher`

## ورود اطلاعات: فقط فایل جامع مدرسه

برای **Import جدید عمومی** فقط مسیر جامع فعال است:

```text
import_type = comprehensive_school
```

قالب رسمی:

```text
Backend/docs/import_templates/comprehensive_school_template.xlsx
```

API دانلود قالب:

```http
GET /api/v1/imports/templates/comprehensive_school/
```

API ایجاد Import:

```http
POST /api/v1/imports/
Content-Type: multipart/form-data
```

فیلدهای اصلی:

```text
school
import_type=comprehensive_school
source_file=<xlsx>
```

قواعد فعلی:

- فقط `.xlsx`
- حداکثر حجم ۱۰ MB
- School باید داخل Scope قابل‌دسترسی کاربر باشد
- فایل تکراری بر اساس checksum و Scope رد می‌شود
- Importهای جدید `students`, `enrollments`, `scores`, `monthly_evaluations` از API عمومی پذیرفته نمی‌شوند
- Import typeهای قدیمی در Model باقی مانده‌اند تا Jobهای تاریخی readable/retryable باشند
- نبودن رکورد در فایل جدید **هیچ‌وقت به معنی حذف نیست**
- خروجی Import سیاست حذف را با `delete_policy = explicit_manual_only` و `records_deleted = 0` گزارش می‌کند

سه Sheet ورودی رسمی:

1. `کلاس‌بندی`
2. `دانش‌آموزان`
3. `ثبت اطلاعات`

کد ملی دانش‌آموز باید دقیقاً ۱۰ رقم باشد. کد کوتاه دیگر با zero-padding مخفی اصلاح نمی‌شود. در Sheet ارزیابی، اگر کد ملی، نام یا کد کلاس قابل مشاهده باشد با اطلاعات Sheet دانش‌آموزان Cross-check می‌شود.

جزئیات کامل Import و ساختار Template در:

- [`docs/COMPREHENSIVE_IMPORT_AND_MANUAL_ENTRY_FA.md`](docs/COMPREHENSIVE_IMPORT_AND_MANUAL_ENTRY_FA.md)

## ثبت و ویرایش دستی

Frontend مسیر مستقل زیر را دارد:

```text
/manual-entry
```

هدف این بخش این است که کاربر برای ثبت دستی مجبور به کار با UUID یا فرم‌های خام و مبهم نباشد. UUID همچنان شناسه فنی داخلی سیستم است، اما Relationها با نام/کد و Picker انتخاب می‌شوند.

گروه‌های راهنمای ثبت دستی:

1. ساختار مدرسه
2. دانش‌آموز و خانواده
3. برنامه درسی و ارزیابی
4. حضور و غیاب
5. کاربران و دسترسی

Enrollment همچنان Workflow اختصاصی دارد؛ تغییر کلاس، انتقال و تغییر وضعیت نباید با Update خام تاریخچه انجام شود.

## ارزیابی جامع ماهانه دستی

Endpointهای جدید رسمی:

```http
GET    /api/v1/monthly-evaluations/catalog/
POST   /api/v1/monthly-evaluations/manual/
DELETE /api/v1/monthly-evaluations/{id}/manual/?reason=...
```

ویژگی‌ها:

- ۷۴ شاخص رسمی با امتیاز `0..5`
- انتخاب Enrollment فعال در Scope مجاز
- انتخاب ماه `1..12`
- Partial save مجاز است
- Metric ارسال‌نشده حفظ می‌شود و پاک نمی‌شود
- Update روی همان `(enrollment, month, framework)` انجام می‌شود
- رکورد soft-deleted قابل Restore است
- `source_import_job` اولیه در ویرایش دستی حفظ می‌شود
- Delete منطقی است، دلیل ۳ تا ۱۰۰۰ کاراکتر می‌خواهد و Audit ثبت می‌شود
- Teacher فقط داخل Class Scope مجاز خود می‌تواند بنویسد

## Update و Delete Policy

قواعد اصلی Data Integrity:

- Excel جامع = Upsert، نه Replace-all
- Missing row در Excel = No delete
- Monthly Evaluation = Upsert + audited soft-delete
- Enrollment = state transition / transfer / change-class؛ نه CRUD خام destructive
- داده‌های تاریخی باید حفظ شوند
- رکوردهای Approved/Locked باید فقط از Workflowهای مجاز تغییر کنند

## قرارداد API

Contract رسمی در این Branch:

- [`contracts/openapi.yaml`](contracts/openapi.yaml)
- [`contracts/API_CHANGELOG.md`](contracts/API_CHANGELOG.md)
- [`contracts/README.md`](contracts/README.md)

تولید OpenAPI در Repository کامل:

```bash
cd Backend
./scripts/generate_openapi.sh ../contracts/openapi.yaml
```

CI Backend Schema تازه تولید می‌کند، Validation انجام می‌دهد و آن را با نسخه Commit‌شده Diff می‌کند. CI Frontend نیز API catalog را regenerate می‌کند و هرگونه Drift نسبت به فایل‌های Commit‌شده را Fail می‌کند.

## API Client Frontend

Frontend از Registry مرکزی استفاده می‌کند. صفحات نباید pathهای API را به شکل literal به `apiRequest` ارسال کنند. عملیات جدید Monthly Evaluation نیز از Operation IDهای OpenAPI در `Frontend/src/api/endpoints.ts` resolve می‌شوند.

راهنمای کامل:

- [`docs/FRONTEND_HANDOFF_FA.md`](docs/FRONTEND_HANDOFF_FA.md)

## Docker Local Stack

در Repository کامل، `docker-compose.yml` سرویس‌های PostgreSQL، Redis، release/migrations، Django، Celery worker، Celery beat و Frontend را بالا می‌آورد.

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f web frontend db
```

URLهای توسعه معمول:

| سرویس | URL |
|---|---|
| Frontend | `http://localhost:5173` |
| API از Frontend | `http://localhost:5173/api/v1/` |
| API مستقیم | `http://localhost:8000/api/v1/` |
| Readiness | `http://localhost:5173/api/v1/health/ready/` |
| Swagger | `http://localhost:5173/api/v1/docs/` |
| ReDoc | `http://localhost:5173/api/v1/redoc/` |
| Admin | `http://localhost:5173/admin/` |

## Validation و CI

### Backend

```bash
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest --cov=hamamooz --cov-report=term-missing
```

آخرین CI بررسی‌شده:

- `137 passed`
- Coverage: `80.08%`
- Ruff: pass
- Django check: pass
- Migration drift: none
- OpenAPI: generated + validated + committed diff pass
- Redis/Celery smoke: pass
- private S3/MinIO smoke: pass
- PostgreSQL backup/restore drill: pass
- production dependency audit: no known vulnerabilities

### Frontend

```bash
npm run typecheck
npm run lint
npm test
npm run build
```

آخرین CI بررسی‌شده:

- `21 passed`
- typecheck: pass
- lint: pass
- production build: pass
- dependency audit: 0 vulnerabilities
- generated API catalog drift check: pass

جزئیات:

- [`docs/CI_AND_CONTRACT_WORKFLOW_FA.md`](docs/CI_AND_CONTRACT_WORKFLOW_FA.md)

## هشدارهای غیرمسدودکننده فعلی

1. `drf-spectacular` هنگام Schema generation برای چند ChoiceField با نام `status` یک enum collision warning می‌دهد و نامی مانند `Status6f2Enum` تولید می‌کند. Schema خطا ندارد، ولی بهتر است بعداً `ENUM_NAME_OVERRIDES` دقیق اضافه شود.
2. GitHub Actions درباره Node.js 20 در Actionهای فعلی deprecation warning می‌دهد. Build و Test فعلاً سبز است؛ ارتقا به Node 24 بهتر است در Maintenance PR جدا انجام شود.

## مستندات این Branch

- [`docs/CURRENT_IMPLEMENTATION_2026-08-08_FA.md`](docs/CURRENT_IMPLEMENTATION_2026-08-08_FA.md) — Snapshot دقیق Feature/PR #4
- [`docs/COMPREHENSIVE_IMPORT_AND_MANUAL_ENTRY_FA.md`](docs/COMPREHENSIVE_IMPORT_AND_MANUAL_ENTRY_FA.md) — Import جامع، ثبت دستی، Update/Delete و Identity
- [`docs/FRONTEND_HANDOFF_FA.md`](docs/FRONTEND_HANDOFF_FA.md) — قرارداد اجرایی Frontend/Backend
- [`docs/CI_AND_CONTRACT_WORKFLOW_FA.md`](docs/CI_AND_CONTRACT_WORKFLOW_FA.md) — CI، تست، Contract generation و Expected outputs
- [`docs/INTEGRATION_MATRIX.md`](docs/INTEGRATION_MATRIX.md) — وضعیت جریان‌های Integration کلیدی
- [`docs/API_CHANGE_TEMPLATE.md`](docs/API_CHANGE_TEMPLATE.md) — Template ثبت تغییرات API
- [`contracts/API_CHANGELOG.md`](contracts/API_CHANGELOG.md) — Changelog رسمی API

## قواعد توسعه

برای تغییر مهم:

1. کد و مستندات مرتبط را بررسی کن.
2. Root cause / requirement را مشخص کن.
3. کوچک‌ترین طراحی درست را انتخاب کن.
4. Domain integrity و Scope را در Backend enforce کن.
5. Migration لازم را بساز؛ Migration history را بازنویسی نکن.
6. Testهای permission، tenant isolation، validation، state transition و regression را اضافه کن.
7. OpenAPI را regenerate کن.
8. Frontend catalog/client را regenerate و compatibility را بررسی کن.
9. Backend/Frontend validation را اجرا کن.
10. در PR فایل‌ها، رفتار، ریسک، migration و breaking change را صریح گزارش کن.

## License

در Snapshot فعلی فایل License در Repository وجود ندارد. برای توزیع مجدد یا استفاده مشتق‌شده باید مجوز مالک Repository بررسی شود.
