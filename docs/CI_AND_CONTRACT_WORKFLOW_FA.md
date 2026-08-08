# CI، Test و API Contract Workflow

این سند وضعیت CI/Contract پروژه را بر اساس PR #4 و Runهای موفق 2026-08-08 ثبت می‌کند.

## 1. هدف CI

CI فقط «تست واحد» نیست. برای HamAmoz باید هم‌زمان این ریسک‌ها را کنترل کند:

- dependency drift/vulnerability
- style/lint drift
- Django configuration errors
- migration drift
- PostgreSQL migration correctness
- OpenAPI drift
- generated frontend catalog drift
- Redis/Celery connectivity
- private object-storage behavior
- backend regressions
- frontend type/build regressions
- backup/restore viability

## 2. Backend Workflow

فایل Repository کامل:

```text
.github/workflows/backend-ci.yml
```

Trigger جدید PR شامل `backend/hardening` است و push روی `backend/**` نیز پوشش داده می‌شود.

### مراحل

#### 2.1 Install

```bash
pip install -r requirements/dev.txt
```

#### 2.2 Dependency consistency

```bash
python -m pip check
```

Expected:

```text
No broken requirements found.
```

#### 2.3 Production dependency audit

```bash
pip-audit -r requirements/production.txt
```

آخرین Expected/Actual:

```text
No known vulnerabilities found
```

#### 2.4 Ruff lint

```bash
ruff check .
```

آخرین نتیجه:

```text
All checks passed!
```

#### 2.5 Ruff format

```bash
ruff format --check --diff hamamooz config tests
```

آخرین نتیجه:

```text
136 files already formatted
```

#### 2.6 Django system check

```bash
python manage.py check
```

آخرین نتیجه:

```text
System check identified no issues (0 silenced).
```

#### 2.7 Migration drift

```bash
python manage.py makemigrations --check --dry-run
```

آخرین نتیجه:

```text
No changes detected
```

#### 2.8 Apply migrations on PostgreSQL

```bash
python manage.py migrate --noinput
```

CI از PostgreSQL service واقعی استفاده می‌کند. این موضوع برای constraint و lock behavior مهم است.

#### 2.9 Generate + validate OpenAPI

```bash
python manage.py spectacular \
  --api-version v1 \
  --file ../contracts/openapi.generated.yaml \
  --validate
```

آخرین نتیجه:

```text
Errors: 0
Warnings: 1
```

Warning فعلی فقط enum naming collision است؛ schema generation fail نشده است.

#### 2.10 Upload generated OpenAPI artifact

Artifact:

```text
openapi-generated
```

Retention فعلی CI:

```text
7 days
```

این Artifact برای review تفاوت schema مفید است.

#### 2.11 Verify committed OpenAPI

```bash
diff -u \
  ../contracts/openapi.yaml \
  ../contracts/openapi.generated.yaml
```

اگر Backend schema تغییر کند ولی Contract commit نشود، CI باید Fail شود.

#### 2.12 Redis/Celery smoke

CI:

- Redis ping می‌کند
- Celery broker connection باز می‌کند

این تست جای worker integration کامل را نمی‌گیرد، ولی misconfiguration واضح Broker را پیدا می‌کند.

#### 2.13 S3/MinIO smoke

CI یک MinIO private bucket موقت می‌سازد و بررسی می‌کند:

- bucket creation
- versioning enabled
- put object
- get object
- delete object

این تست برای مسیر storage-compatible با S3 است.

#### 2.14 Backend tests + coverage

```bash
pytest --cov=hamamooz --cov-report=term-missing --cov-report=xml
```

آخرین نتیجه:

```text
137 passed
1 warning
177.56s
coverage = 80.08%
required = 78%
```

Coverage XML به عنوان Artifact آپلود می‌شود:

```text
backend-coverage
```

#### 2.15 PostgreSQL backup/restore drill

CI:

1. backup می‌گیرد
2. database restore جداگانه می‌سازد
3. dump را restore می‌کند
4. وجود migration rows را verify می‌کند

آخرین drill موفق بوده است.

## 3. Backend CI Run مبنا

```text
Run ID: 31248852083
Job: backend-quality
Conclusion: success
```

این Run روی PR merge ref مربوط به HEAD `c30d0a57...` اجرا شده است.

## 4. Frontend Workflow

فایل Repository کامل:

```text
.github/workflows/frontend-ci.yml
```

Trigger جدید شامل PR به `backend/hardening` و push روی `frontend/**` و `backend/**` برای تغییرات مرتبط با Frontend/Contract است.

## 5. Frontend مراحل CI

### 5.1 npm ci

```bash
npm ci
```

### 5.2 dependency audit

```bash
npm audit --audit-level=high
```

آخرین نتیجه:

```text
0 vulnerabilities
```

### 5.3 Contract generator dependency

CI Python/PyYAML را برای script تولید catalog آماده می‌کند.

### 5.4 Generate API catalog

```bash
npm run generate:api
```

آخرین خروجی:

```text
173 operations
170 schemas
```

Generated files:

```text
Frontend/src/api/generated/catalog.json
Frontend/src/api/generated/catalog.ts
```

### 5.5 Upload generated catalog artifact

Artifact:

```text
frontend-api-catalog
```

### 5.6 Verify committed generated catalog

```bash
git diff --exit-code -- src/api/generated
```

هر Drift باید CI را Fail کند.

### 5.7 Typecheck

```bash
npm run typecheck
```

فعلی:

```text
tsc --noEmit
PASS
```

### 5.8 Lint

```bash
npm run lint
```

فعلی:

```text
Static lint checks passed.
```

### 5.9 Test + Build

```bash
npm test
```

Test script فعلی ابتدا production build انجام می‌دهد و سپس Node tests را اجرا می‌کند.

آخرین نتیجه:

```text
21 tests
21 pass
0 fail
```

موارد مهم Testشده شامل:

- custom action serializer consistency
- no inferred unsafe serializer overrides
- import route browser resolution
- import multipart field correctness
- official student analytics endpoint usage
- enum localization
- no raw JSON rendering in generic UI
- relation picker behavior
- production assets
- generated catalog expected surface
- comprehensive-only import enum
- critical auth/dashboard endpoints
- operational endpoints
- endpoint registry contract consistency
- no literal endpoints passed to apiRequest
- field error mapping
- wrapped API error metadata
- network failure message
- shared token refresh
- session restoration
- access token not persisted in browser storage

## 6. Frontend CI Run مبنا

```text
Run ID: 31248852078
Job: frontend-quality
Conclusion: success
```

## 7. Contract Change Rule

هر API behavior change که client را تحت تأثیر قرار دهد باید حداقل این مسیر را طی کند:

```text
Backend code
-> backend tests
-> generate OpenAPI
-> validate OpenAPI
-> commit contracts/openapi.yaml
-> update API changelog
-> regenerate frontend catalog
-> update endpoint registry if needed
-> frontend typecheck/lint/test/build
-> CI drift checks
```

## 8. OpenAPI Source Rule

فایل:

```text
contracts/openapi.yaml
```

Generated output است.

ممنوع:

```text
manual edit to make CI green
```

درست:

```text
fix backend schema annotations/serializers/views
then regenerate OpenAPI
```

## 9. Breaking Change Rule

Breaking change باید:

- در `contracts/API_CHANGELOG.md` ثبت شود
- migration path داشته باشد
- frontend compatibility بررسی شود
- generated catalog regenerate شود
- CI سبز باشد

Breaking change فعلی Import:

```text
new public imports: comprehensive_school only
```

Legacy Jobها برای history باقی مانده‌اند.

## 10. Test Priority برای تغییرات Domain

### Tenant/permission

- cross-organization
- cross-school
- cross-class
- teacher scope
- object permission
- invalid UUID outside scope

### State transitions

- enrollment transfer/change class/status
- assessment submit/approve/lock
- soft-delete/restore
- retry/cancel jobs

### Import

- invalid headers
- invalid identity
- duplicate file
- transaction rollback
- no implicit delete
- idempotent/retry-safe behavior

### Calculation

- deterministic result
- policy version
- rounding
- locked/approved records

### Contract

- request schema
- response schema
- enum
- status codes
- query/path params

## 11. PostgreSQL Reference

برای workflowهایی که lock/concurrency اهمیت دارد، PostgreSQL مرجع است. SQLite نباید نتیجه locking را نمایندگی کند.

Featureهای جدید `select_for_update` در Import job state و Monthly Evaluation استفاده می‌کنند؛ تست concurrency واقعی در صورت اضافه شدن باید روی PostgreSQL انجام شود.

## 12. Coverage Interpretation

```text
80.08% >= 78%
```

این به معنی «همه حالت‌ها تست شده‌اند» نیست.

نقاط فعلی با پوشش پایین‌تر که ارزش Follow-up دارند:

```text
imports/tasks.py          ~33%
imports/pipeline.py       ~65%
attendance/notifications  ~58%
attendance/validators     ~60%
```

Featureهای اصلی جدید پوشش بالاتری دارند:

```text
evaluations/manual.py              ~96%
imports/comprehensive_hardening.py ~90%
imports/serializers.py             ~87%
imports/views.py                   ~86%
```

## 13. Known Warning — OpenAPI Enum Name

`drf-spectacular` برای چند field با نام `status` collision می‌بیند و نامی مثل:

```text
Status6f2Enum
```

می‌سازد.

فعلاً:

```text
validation errors = 0
```

Follow-up پیشنهادی:

- Domain enum را مشخص کن
- `SPECTACULAR_SETTINGS.ENUM_NAME_OVERRIDES` اضافه کن
- regenerate contract
- ensure frontend catalog stable

## 14. Known Warning — Node 20

GitHub Actions درباره Node.js 20 deprecation warning می‌دهد.

فعلاً Frontend با:

```text
Node 20.20.2
npm 10.8.2
```

pass شده است.

Follow-up:

- Node 24 را در maintenance branch امتحان کن
- npm ci/typecheck/lint/test/build را کامل اجرا کن
- سپس workflow version را تغییر بده

## 15. Merge Gate پیشنهادی

برای PRهای مشابه، Merge فقط وقتی انجام شود که:

```text
Backend CI = green
Frontend CI = green (اگر Frontend/contract affected)
Migration drift = none
OpenAPI drift = none
Generated catalog drift = none
Security/scope review = done
Breaking change = documented
```

## 16. Artifactها

Artifactهای فعلی CI برای Debug/Review:

```text
openapi-generated
backend-coverage
frontend-api-catalog
```

Retention فعلی 7 روز است؛ فایل Commit‌شده همچنان Source of Truth است، نه Artifact موقت.
