# راهنمای اتصال Frontend به Backend هم‌آموز

این سند قرارداد اجرایی Frontend و Backend است. نسخه حاضر در تاریخ **2026-08-08** با `backend/comprehensive-manual-hardening` / PR #4 همگام شده و جایگزین راهنمای قدیمی مبتنی بر `backend/mvp-bootstrap` می‌شود.

هدف اصلی: Frontend نباید Endpoint، Payload، Response، Enum، Scope یا Permission را حدس بزند و نباید امنیت Tenant/School را با فیلتر سمت مرورگر پیاده‌سازی کند.

## 1. Source of Truth

ترتیب مرجع:

1. کد جاری
2. Testها و Migrationها
3. Schema زنده/تولیدشده OpenAPI
4. `contracts/openapi.yaml`
5. Architecture/decision docs
6. README
7. Assumption

Contract ماشین‌خوان Commit‌شده:

```text
contracts/openapi.yaml
```

Changelog:

```text
contracts/API_CHANGELOG.md
```

در Snapshot فعلی این فایل‌ها با Feature Branch `backend/comprehensive-manual-hardening` و commit `c30d0a57d1d05c77b295797dae4e652295174e4e` همگام شده‌اند.

اگر Schema تولیدشده Backend با `contracts/openapi.yaml` اختلاف داشته باشد، Integration باید متوقف شود. CI این Drift را Fail می‌کند.

**OpenAPI را دستی ویرایش نکنید.**

## 2. Generated API Catalog

Frontend یک catalog تولیدشده از OpenAPI دارد:

```text
Frontend/src/api/generated/catalog.json
Frontend/src/api/generated/catalog.ts
```

فرمان تولید:

```bash
cd Frontend
npm run generate:api
```

آخرین خروجی CI بررسی‌شده:

```text
173 operations
170 schemas
```

CI بعد از regenerate این مسیر را بررسی می‌کند:

```bash
git diff --exit-code -- src/api/generated
```

هر Diff یعنی Contract یا catalog Commit‌شده قدیمی است.

## 3. Endpoint Registry مرکزی

صفحات و Componentها نباید path literal را مستقیماً به `apiRequest` بدهند. Registry مرکزی فعلی:

```text
Frontend/src/api/endpoints.ts
```

Operation pathها با Operation ID قرارداد resolve می‌شوند. مثال عملیات جدید ارزیابی ماهانه:

```text
monthly_evaluations_catalog_retrieve
monthly_evaluations_manual_create
monthly_evaluations_manual_destroy
```

قاعده:

```text
OpenAPI -> generated catalog -> endpoint registry -> page/component
```

نه:

```text
page -> hard-coded /api/v1/...
```

تست Frontend بررسی می‌کند Registry فقط به Operation IDهای موجود در OpenAPI اشاره کند و صفحات literal endpoint به `apiRequest` ندهند.

## 4. Base URL

Local backend direct:

```text
http://localhost:8000/api/v1/
```

Local through frontend/Nginx:

```text
http://localhost:5173/api/v1/
```

Base URL باید فقط از Configuration مرکزی گرفته شود. Component، Store یا Page نباید Base URL بسازد.

## 5. Authentication

### Login

```http
POST /api/v1/auth/token/
Content-Type: application/json
```

```json
{
  "username": "...",
  "password": "..."
}
```

### Current user

```http
GET /api/v1/auth/me/
Authorization: Bearer <access-token>
```

Role و Scope باید از پاسخ معتبر Backend/Session state گرفته شوند؛ UI نباید آن‌ها را حدس بزند.

### Refresh

```http
POST /api/v1/auth/token/refresh/
```

Client مرکزی باید shared refresh داشته باشد تا چند 401 هم‌زمان چند Refresh Request موازی نسازند.

### Logout

```http
POST /api/v1/auth/logout/
```

Access token نباید در browser storage پایدار شود. Test فعلی Frontend این invariant را بررسی می‌کند.

## 6. Roleها

Roleهای Backend فعلی:

```text
system_admin
organization_admin
school_manager
educational_deputy
operator
teacher
```

Frontend می‌تواند برای UX Card/Button را بر اساس Role مخفی کند، اما این رفتار **Authorization نیست**. Backend باید همان دسترسی را مستقل enforce کند.

## 7. Scope Headerها

Headerهای مهم:

```http
Authorization: Bearer <token>
X-School-ID: <school-uuid>
X-Organization-ID: <organization-uuid>
X-Request-ID: <uuid>
```

قواعد:

- Scope فعال باید در Session/Application state مرکزی باشد.
- Component نباید Scope header را خودش بسازد.
- با تغییر Scope، Query/Cache وابسته باید invalidate شود.
- School یا Organization خارج از دسترسی کاربر نباید با Frontend filtering «امن» فرض شود.
- UUID در payload می‌تواند از کاربر مخفی باشد، اما Backend باید Object Scope آن را validate کند.

## 8. Pagination

List response استاندارد:

```json
{
  "count": 120,
  "next": "...",
  "previous": null,
  "results": []
}
```

پارامترهای رایج:

```text
page
page_size
search
ordering
```

هر Endpoint ممکن است filterهای Domain-specific دیگری هم داشته باشد؛ فقط از Contract بخوانید.

## 9. Error Handling

قالب wrapper عمومی Backend:

```json
{
  "error": {
    "code": "validation_error",
    "detail": {},
    "request_id": "..."
  }
}
```

رفتار UI مورد انتظار:

| Status | رفتار |
|---|---|
| `400` | Field validation / workflow error را واضح نمایش بده |
| `401` | shared refresh؛ در شکست Session را خاتمه بده |
| `403` | عدم دسترسی/Scope نامعتبر |
| `404` | نبود رکورد یا خارج بودن آن از Scoped queryset |
| `409` | conflict/state transition conflict |
| `429` | retry سریع انجام نده |
| `503` | وضعیت موقت unavailable و retry کنترل‌شده |
| Network | داده فرم را حفظ کن و retry بده |

`request_id` برای Bug report باید قابل دسترسی باشد، بدون افشای داده حساس.

## 10. Relation Picker و UUID

UUID شناسه فنی داخلی است. کاربر نهایی نباید مجبور شود UUID را تایپ/کپی کند.

فرم‌های Schema-based باید Relationها را با گزینه‌های خوانا نشان دهند، مثل:

- School name/code
- Academic year title/code
- Grade title
- Class name/code
- Student name / national id / student number
- Enrollment label
- Teacher/user name
- Subject/title

Backend همچنان UUID را به‌عنوان identity فنی دریافت می‌کند؛ Frontend فقط انتخاب آن را human-readable می‌کند.

## 11. مسیر «ثبت و ویرایش دستی»

Route:

```text
/manual-entry
```

این صفحه یک Hub راهنما است، نه Backend جداگانه. برای Resourceهای معمول از همان endpointهای رسمی Domain و Schema تولیدشده استفاده می‌کند.

گروه‌ها:

### 11.1 ساختار مدرسه

- organizations
- schools
- academic-years
- terms
- grade-levels
- classes

### 11.2 دانش‌آموز و خانواده

- students
- guardians
- enrollments

### 11.3 برنامه درسی و ارزیابی

- subjects
- grade-subjects
- course-offerings
- assessment-types
- assessments
- scores
- monthly-evaluations
- calculation-policies

### 11.4 حضور و غیاب

- attendance-policies
- attendance-sessions
- attendance-records

### 11.5 کاربران و دسترسی

- users
- role-assignments

هر Card باید توضیح ساده، dependency/order tip، «ثبت جدید» و «مشاهده و ویرایش» داشته باشد.

Enrollment exception مهم است: انتقال/تغییر کلاس/تغییر وضعیت باید با Actionهای اختصاصی انجام شود، نه ویرایش خام رکورد تاریخی.

## 12. Public Import Policy

برای Import جدید فقط فایل جامع رسمی فعال است.

### Template

```http
GET /api/v1/imports/templates/comprehensive_school/
```

### Create

```http
POST /api/v1/imports/
Content-Type: multipart/form-data
```

Payload:

```text
school=<uuid selected by relation picker>
import_type=comprehensive_school
source_file=<official .xlsx>
```

قواعد Backend:

- فقط `comprehensive_school`
- فقط `.xlsx`
- حداکثر 10 MB
- School باید accessible باشد
- checksum تکراری در همان Scope برای Job queued/processing/completed رد می‌شود
- legacy import types برای historical jobها باقی مانده‌اند، ولی create جدید ندارند

Frontend نباید UI انتخاب template/typeهای قدیمی را نشان دهد.

### Job actions

ImportJobهای مجاز در Scope دارای عملیات رسمی هستند:

```http
GET  /api/v1/imports/
GET  /api/v1/imports/{id}/
POST /api/v1/imports/{id}/retry/
POST /api/v1/imports/{id}/cancel/
GET  /api/v1/imports/{id}/errors/
```

Retry فقط برای failed یا processing stale؛ Cancel فقط queued/processing.

## 13. File Comprehensive Result UX

Frontend باید `result_summary` را به‌جای یک پیام مبهم «موفق شد» نمایش دهد. فیلدهای مهم جدید:

```text
classes_created / classes_updated / classes_unchanged
students_created / students_updated / students_unchanged
enrollments_created / enrollments_updated / enrollments_unchanged
evaluations_created / evaluations_updated / evaluations_unchanged
metric_scores_created / metric_scores_updated / metric_scores_unchanged
records_deleted = 0
delete_policy = explicit_manual_only
template_version
source = comprehensive_school
```

قاعده UX: نبودن رکورد در فایل جدید نباید در UI به «حذف شد» تعبیر شود.

## 14. Monthly Evaluation Catalog

```http
GET /api/v1/monthly-evaluations/catalog/
```

Response shape:

```json
{
  "framework_version": "...",
  "score_min": 0,
  "score_max": 5,
  "metric_count": 74,
  "metrics": [
    {
      "code": "EDU_01",
      "title": "...",
      "domain_code": "...",
      "domain_title": "...",
      "domain_weight": 20,
      "order": 1
    }
  ]
}
```

Frontend نباید ۷۴ شاخص را جداگانه Hardcode کند؛ Catalog Backend مرجع تعریف Metricهاست.

## 15. Manual Monthly Evaluation

### Create / Update

```http
POST /api/v1/monthly-evaluations/manual/
Content-Type: application/json
```

Payload:

```json
{
  "enrollment": "<uuid>",
  "month_no": 4,
  "note": "توضیح اختیاری",
  "metrics": [
    {"metric_code": "EDU_01", "value": 4},
    {"metric_code": "DEV_01", "value": 5}
  ]
}
```

Validation:

- `enrollment`: UUID یک Enrollment فعال و accessible
- `month_no`: `1..12`
- `note`: حداکثر 5000
- `metrics`: اختیاری، مقدار هر Metric `0..5`
- Metric code در یک Request نباید تکراری باشد
- حداقل یک Metric یا note لازم است

Semantics:

- اگر Evaluation وجود ندارد، create
- اگر وجود دارد، update همان رکورد
- Metric ارسال‌نشده حفظ می‌شود
- اگر Evaluation soft-delete شده باشد، restore می‌شود
- provenance اولیه `source_import_job` حفظ می‌شود

Response:

```json
{
  "evaluation": {"id": "..."},
  "result": {
    "created": false,
    "restored": false,
    "metrics_created": 0,
    "metrics_updated": 2,
    "metrics_unchanged": 0
  }
}
```

Status موفق می‌تواند `201` برای create یا `200` برای update باشد.

## 16. Delete Monthly Evaluation

```http
DELETE /api/v1/monthly-evaluations/{id}/manual/?reason=<text>
```

قواعد:

- reason اجباری
- طول `3..1000`
- soft-delete
- metric history حفظ می‌شود
- Audit event ثبت می‌شود
- detail lookup از Scoped queryset انجام می‌شود

Frontend باید عبارت «حذف منطقی» و حفظ سابقه را واضح توضیح دهد.

## 17. Monthly Evaluation Form UX

فرم فعلی باید:

- Enrollment فعال را با نام دانش‌آموز / student number / class نمایش دهد
- search server-side داشته باشد
- ماه را فارسی نمایش دهد ولی `month_no` عددی ارسال کند
- Metricها را بر اساس Domain گروه‌بندی کند
- blank Metric را «بدون تغییر» تفسیر کند
- Existing Evaluation را load و prefill کند
- save partial را مجاز بداند
- entered count را نشان دهد
- delete را فقط وقتی رکورد موجود است نشان دهد
- reason برای delete بگیرد

## 18. Security نکات ویژه Frontend

Frontend نباید:

- Enrollment خارج از Scope را با query عمومی fetch کند
- Teacher را فقط با مخفی کردن UI محدود کند
- ID قابل حدس یا UUID از URL را trusted فرض کند
- `source_import_job`, tenant ids یا audit fields را خودسرانه mutate کند
- national ID یا PII را در console/log ثبت کند
- Error response کامل حاوی PII را به monitoring بدون redaction بفرستد

## 19. Contract Change Workflow

Backend:

1. API behavior را تغییر بده
2. Test اضافه/اصلاح کن
3. `python manage.py spectacular --api-version v1 --file ../contracts/openapi.generated.yaml --validate`
4. Diff را review کن
5. `contracts/openapi.yaml` را regenerate/commit کن
6. `contracts/API_CHANGELOG.md` را update کن

Frontend:

1. OpenAPI diff را review کن
2. `npm run generate:api`
3. endpoint registry را در صورت نیاز update کن
4. typecheck/lint/test/build را اجرا کن
5. generated catalog drift نداشته باشد

## 20. CI Expected Results

Backend checks:

```text
pip check
pip-audit
ruff check
ruff format --check --diff
python manage.py check
makemigrations --check --dry-run
migrate
OpenAPI generate + validate
OpenAPI committed diff
Redis/Celery smoke
S3/MinIO smoke
pytest + coverage
PostgreSQL backup/restore drill
```

آخرین نتیجه:

```text
137 passed
coverage 80.08% >= 78%
0 OpenAPI errors
```

Frontend checks:

```text
npm ci
npm audit --audit-level=high
npm run generate:api
generated catalog diff
npm run typecheck
npm run lint
npm test
production build
```

آخرین نتیجه:

```text
21 passed
0 frontend dependency vulnerabilities
```

## 21. Known Non-blocking Warnings

- OpenAPI enum naming collision برای چند `status` choice؛ خروجی فعلی نامی مثل `Status6f2Enum` دارد. Contract valid است، ولی naming باید بعداً override شود.
- GitHub Actions برای Node.js 20 deprecation warning می‌دهد؛ Migration به Node 24 بهتر است Maintenance جدا باشد.

## 22. Definition of Frontend Integration Done

یک Feature زمانی از نظر Integration کامل است که:

- Operation در OpenAPI وجود داشته باشد
- generated catalog sync باشد
- endpoint registry از Operation ID استفاده کند
- payload/response Type با Contract یکی باشد
- loading/empty/error state وجود داشته باشد
- scope/role UX درست باشد
- Backend مستقل authorization را enforce کند
- regression test وجود داشته باشد
- typecheck/lint/test/build pass باشند
- Breaking change در Changelog ثبت شده باشد

## 23. Bug Report مرتبط با API

Bug report مفید شامل:

- Environment
- Route UI
- Endpoint + Method
- role
- active organization/school
- payload با حذف PII/secret
- status code
- normalized error
- `request_id`
- steps to reproduce
- expected/actual behavior

Token، password و PII غیرضروری نباید داخل Issue قرار بگیرند.
