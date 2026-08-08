# وضعیت جاری پیاده‌سازی HamAmoz — 2026-08-08

این سند Snapshot فنی تغییرات PR #4 (`backend/comprehensive-manual-hardening`) است و برای ثبت دقیق رفتار فعلی Backend، Frontend، Contract، CI و ریسک‌های باقی‌مانده نوشته شده است.

## مبنای Snapshot

```text
Repository: leonardo0231/hamamooz-platform
Feature branch: backend/comprehensive-manual-hardening
PR: #4
Base: backend/hardening
Head: c30d0a57d1d05c77b295797dae4e652295174e4e
State at snapshot: open, mergeable
```

## 1. هدف تغییرات

Scope تکمیل‌شده شامل این موارد است:

1. محدود کردن Import عمومی به فایل جامع مدرسه
2. سخت‌گیری هویتی فایل جامع
3. خروجی دقیق created/updated/unchanged
4. عدم حذف ضمنی اطلاعات با غیبت از Excel
5. ایجاد پنل جداگانه و ساده ثبت دستی
6. ساده‌سازی UX شناسه‌ها و Relationها
7. ایجاد API امن برای ثبت/ویرایش/حذف منطقی ارزیابی جامع ماهانه
8. تکمیل OpenAPI و generated frontend catalog
9. تکمیل regression test و CI validation

## 2. فایل‌های اصلی Backend تحت تأثیر

### Import

```text
Backend/hamamooz/apps/imports/comprehensive.py
Backend/hamamooz/apps/imports/comprehensive_hardening.py
Backend/hamamooz/apps/imports/pipeline.py
Backend/hamamooz/apps/imports/serializers.py
Backend/hamamooz/apps/imports/views.py
Backend/hamamooz/apps/imports/tasks.py
```

### Monthly Evaluation

```text
Backend/hamamooz/apps/evaluations/manual.py
Backend/hamamooz/apps/evaluations/serializers.py
Backend/hamamooz/apps/evaluations/views.py
```

### Contract / tests

```text
Backend/tests/test_api_workflows.py
Backend/tests/test_hardening_completion.py
Backend/tests/test_monthly_evaluations.py
Backend/tests/test_openapi_schema.py
contracts/openapi.yaml
contracts/API_CHANGELOG.md
```

## 3. فایل‌های اصلی Frontend تحت تأثیر

```text
Frontend/src/pages/imports-simple.ts
Frontend/src/pages/manual-entry.ts
Frontend/src/api/endpoints.ts
Frontend/src/app/routes.ts
Frontend/src/app/router.ts
Frontend/src/components/shell.ts
Frontend/src/api/generated/catalog.json
Frontend/src/api/generated/catalog.ts
```

UI Import قدیمی چندنوعی حذف شده و مسیر جدید فقط فایل جامع رسمی را ارائه می‌کند.

## 4. Import عمومی جدید

Public create فقط این مقدار را می‌پذیرد:

```text
comprehensive_school
```

Legacy values هنوز در `ImportJob.ImportType` وجود دارند تا Job تاریخی قابل مشاهده/retry باشد، اما Serializer create آن‌ها را reject می‌کند.

### Validation ورودی

- School باید در `accessible_school_ids(request.user)` باشد.
- Extension باید `.xlsx` باشد.
- Size باید حداکثر 10 MB باشد.
- SHA-256 checksum محاسبه می‌شود.
- Duplicate در همان `(organization, school, import_type, checksum)` برای وضعیت‌های queued/processing/completed رد می‌شود.

### Template endpoint

فقط:

```http
GET /api/v1/imports/templates/comprehensive_school/
```

Templateهای legacy دیگر از public endpoint قابل دانلود نیستند.

### Import Job lifecycle

- create -> queued
- پس از commit، Celery task queue می‌شود
- processing state با row lock تنظیم می‌شود
- failed و stale processing قابل retry هستند
- queued/processing قابل cancel هستند
- error workbook مستقل قابل دانلود است

Error workbook ستون‌های زیر را دارد:

```text
sheet
row
column
code
message
```

## 5. Pipeline جدید Comprehensive

`imports/tasks.py` برای job جدید جامع از `imports/pipeline.py` استفاده می‌کند.

Pipeline:

1. Job را Lock می‌کند.
2. وضعیت processing را ثبت می‌کند.
3. از Loader موجود برای safe workbook loading استفاده می‌کند.
4. ردیف‌های Evaluation را با identity cellهای قابل مشاهده enrich می‌کند.
5. hardened validation را اجرا می‌کند.
6. اگر خطا باشد هیچ write دامنه‌ای انجام نمی‌شود.
7. apply جامع در transaction انجام می‌شود.
8. result summary نوشته می‌شود.

Jobهای تاریخی non-comprehensive در صورت retry به service legacy delegate می‌شوند. Public API اجازه ساخت Job legacy جدید نمی‌دهد.

## 6. Identity Hardening

### National ID

National ID باید **دقیقاً ۱۰ رقم** باشد.

رفتار قدیمی خطرناک:

```text
short id -> zfill(10)
```

در hardened validation دیگر short value repair نمی‌شود. اگر صفر ابتدایی وجود دارد باید در فایل حفظ شده باشد.

### Evaluation identity cross-check

Evaluation همچنان با `local_code` workbook-local به Student sheet متصل می‌شود، اما identity قابل مشاهده نیز بررسی می‌شود:

- national id
- full name
- class code

اگر این cellها nonblank باشند باید با Student sheet تطابق داشته باشند.

Error codeهای اختصاصی شامل مواردی مانند:

```text
national_id_format
evaluation_national_id_format
evaluation_identity_mismatch
evaluation_class_mismatch
evaluation_name_mismatch
```

## 7. Excel Upsert Semantics

Comprehensive import داده‌های زیر را upsert می‌کند:

- ClassSection
- Student
- Enrollment
- MonthlyEvaluation
- MetricScore

قبل از apply، snapshot گرفته می‌شود تا مواردی که واقعاً تغییری ندارند از updated جدا شوند.

Result summary شامل تفکیک:

```text
created
updated
unchanged
```

برای classes/students/enrollments/evaluations و metric scoreهاست.

### Delete policy

قاعده قطعی:

```text
Missing from workbook != delete from database
```

Summary:

```json
{
  "records_deleted": 0,
  "delete_policy": "explicit_manual_only"
}
```

این رفتار برای حفاظت از تاریخچه تحصیلی عمداً طراحی شده است.

## 8. پنل ثبت دستی

Route:

```text
/manual-entry
```

این صفحه یک مسیر guided برای Domain endpointهای رسمی است.

### گروه 1 — ساختار مدرسه

- organization
- school
- academic year
- term
- grade level
- class

### گروه 2 — دانش‌آموز و خانواده

- student
- guardian
- enrollment

### گروه 3 — برنامه درسی و ارزیابی

- subject
- grade-subject
- course-offering
- assessment-type
- assessment
- score
- monthly evaluation
- calculation policy

### گروه 4 — حضور و غیاب

- attendance policy
- attendance session
- attendance record

### گروه 5 — کاربران و دسترسی

- user
- role assignment

## 9. UX شناسه‌ها

UUID حذف نشده است و همچنان identity فنی بسیاری از مدل‌هاست. تغییر اصلی UX این است که کاربر UUID را تایپ نمی‌کند.

Relation pickerها object را با داده خوانا انتخاب می‌کنند:

- name
- title
- code
- student name
- student number
- class title

سپس UUID پشت صحنه در request ارسال می‌شود.

این UX هیچ تأثیری بر Authorization ندارد؛ Backend همچنان Scope UUID را validate می‌کند.

## 10. Enrollment Integrity

Generic CRUD خام برای transitionهای حساس Enrollment باز نشده است.

عملیات تاریخی باید از مسیرهای اختصاصی انجام شوند:

- change class
- transfer
- change status

هدف: Enrollment history، class membership و سابقه انتقال خراب نشود.

## 11. Manual Monthly Evaluation Backend

Service:

```text
Backend/hamamooz/apps/evaluations/manual.py
```

Identity رکورد:

```text
(enrollment, month_no, FRAMEWORK_VERSION)
```

### Upsert

- `select_for_update` روی evaluation موجود
- active رکورد بر deleted اولویت دارد
- deleted موجود می‌تواند restore شود
- note update می‌شود
- `recorded_by` آخرین editor است
- metricهای request upsert می‌شوند
- metricهای omitted حذف یا reset نمی‌شوند
- `source_import_job` روی رکورد موجود overwrite نمی‌شود

### Delete

- row lock
- soft-delete
- metric history باقی می‌ماند

## 12. Manual Monthly Evaluation API

### Catalog

```http
GET /api/v1/monthly-evaluations/catalog/
```

شامل:

- framework version
- score min/max
- metric count
- 74 metric definition

### Upsert

```http
POST /api/v1/monthly-evaluations/manual/
```

ورودی:

```json
{
  "enrollment": "uuid",
  "month_no": 4,
  "note": "optional",
  "metrics": [
    {"metric_code": "EDU_01", "value": 4}
  ]
}
```

Validation:

- month `1..12`
- score `0..5`
- note max `5000`
- duplicate metric code ممنوع
- request کاملاً خالی ممنوع

### Delete

```http
DELETE /api/v1/monthly-evaluations/{id}/manual/?reason=...
```

Reason:

```text
min 3
max 1000
```

Response موفق:

```text
204 No Content
```

## 13. Authorization Monthly Evaluation

Writer roleها:

```text
system_admin
organization_admin
school_manager
educational_deputy
operator
teacher
```

ولی Role به تنهایی کافی نیست.

Enrollment با این Scope resolve می‌شود:

```text
school_id in selected_school_ids(request)
class_section_id in allowed_class_ids(request.user, school_ids)
status = active
```

در نتیجه:

- UUID Enrollment مدرسه دیگر معتبر نیست
- Teacher به کلاس‌های غیرمجاز دسترسی write ندارد
- detail delete نیز از Scoped queryset استفاده می‌کند

## 14. Audit

Manual upsert و delete Audit می‌شوند.

نمونه actionها:

```text
evaluation.manual_upserted
evaluation.manual_deleted
```

Reason/note طبق Audit redaction policy نباید بی‌محافظ در log حساس نشت کنند.

## 15. Frontend Monthly Evaluation UX

Dialog اختصاصی:

- catalog را از Backend می‌گیرد
- active enrollment را server-side search می‌کند
- enrollment را با student name/student number/class نشان می‌دهد
- Persian month label دارد
- 74 metric را domain-grouped نشان می‌دهد
- blank = «ثبت نشده/بدون تغییر»
- existing evaluation را load و prefill می‌کند
- partial save مجاز است
- metric count نمایش می‌دهد
- delete فقط برای existing record فعال می‌شود
- delete reason می‌گیرد

## 16. Contract Changes

OpenAPI جدید شامل endpointهای زیر است:

```text
GET /api/v1/monthly-evaluations/catalog/
POST /api/v1/monthly-evaluations/manual/
DELETE /api/v1/monthly-evaluations/{id}/manual/
```

Import create schema فقط `comprehensive_school` را به‌عنوان enum عمومی expose می‌کند.

Frontend endpoint registry برای عملیات جدید از Operation ID استفاده می‌کند.

Generated contract files:

```text
contracts/openapi.yaml
Frontend/src/api/generated/catalog.json
Frontend/src/api/generated/catalog.ts
```

## 17. Contract Regression Test

`Backend/tests/test_openapi_schema.py` صریحاً بررسی می‌کند:

- catalog response schema
- manual request schema
- manual response 200/201
- delete reason query parameter
- delete 204
- multipart Import create schema
- import type enum = فقط `comprehensive_school`

## 18. Backend CI Result

آخرین Run بررسی‌شده: `31248852083`

نتیجه:

```text
backend-quality: success
```

Checkهای موفق:

- dependency consistency
- production dependency audit
- Ruff lint
- Ruff format
- Django check
- missing migration check
- migrate on PostgreSQL
- OpenAPI generate/validate
- committed OpenAPI diff
- Redis/Celery broker smoke
- MinIO/S3 private storage smoke
- pytest
- coverage artifact
- PostgreSQL backup/restore drill

Test result:

```text
137 passed
1 warning
177.56s
```

Coverage:

```text
80.08%
required: 78%
```

## 19. Frontend CI Result

آخرین Run بررسی‌شده: `31248852078`

```text
frontend-quality: success
```

مراحل موفق:

- npm ci
- npm audit
- PyYAML install for generator
- generate API catalog
- generated catalog diff
- typecheck
- lint
- test
- production build

Test result:

```text
21 passed
0 failed
```

Generated:

```text
173 operations
170 schemas
```

## 20. Coverage نقاط مهم

در آخرین Backend CI:

```text
evaluations/manual.py                 ~96%
imports/comprehensive_hardening.py    ~90%
imports/serializers.py                ~87%
imports/views.py                      ~86%
imports/comprehensive.py              ~84%
imports/pipeline.py                   ~65%
imports/tasks.py                      ~33%
```

این اعداد نشان می‌دهند Featureهای جدید اصلی پوشش مناسبی دارند، اما coverage کلی به معنی اثبات تمام edge caseهای Domain نیست.

## 21. Known Technical Debt / Follow-up

### 21.1 دو مسیر process import

`pipeline.process_import_job` مسیر canonical برای queued comprehensive import است، ولی `services.process_import_job` برای historical/legacy usage باقی مانده است. در آینده بهتر است source of truth processing شفاف‌تر یکپارچه شود، بدون شکستن retry تاریخی.

### 21.2 OpenAPI enum warning

`drf-spectacular` یک warning naming collision برای `status` دارد و component نامی شبیه:

```text
Status6f2Enum
```

می‌سازد. Contract valid است. Follow-up مناسب: `ENUM_NAME_OVERRIDES` با نام Domain-specific.

### 21.3 Node 20 deprecation

GitHub Actions درباره Node 20 warning می‌دهد. ارتقا به Node 24 باید با build/test جدا بررسی شود.

### 21.4 Coverage پایین‌تر در بخش‌های غیر Feature

برخی notification/attendance/task/management commandها هنوز coverage پایین‌تری دارند. این موارد blocker همین PR نیستند ولی باید در hardening incremental پوشش داده شوند.

## 22. Migration Impact

برای Featureهای اصلی این PR Model field جدید ایجاد نشده، بنابراین migration جدید برای manual evaluation/import hardening لازم نبود.

CI نیز:

```text
python manage.py makemigrations --check --dry-run
```

را با نتیجه `No changes detected` پاس کرده است.

## 23. Breaking Change

Public Import API برای create جدید breaking شده است:

قدیمی:

```text
students
enrollments
scores
monthly_evaluations
```

جدید:

```text
comprehensive_school
```

Migration path:

- Bulk import جدید -> فایل جامع
- Single/manual write -> Domain endpoint یا `/manual-entry`
- Historical ImportJob -> همچنان visible/retryable

## 24. Merge Readiness

در Snapshot این سند:

- PR open است
- mergeable است
- Backend CI سبز است
- Frontend CI سبز است
- Contract sync است
- migration drift وجود ندارد
- Security regressionهای Scope اضافه شده‌اند

بنابراین از دید Validation انجام‌شده، Feature برای review/merge آماده است؛ تصمیم merge مستقل از این Branch مستندات است.
