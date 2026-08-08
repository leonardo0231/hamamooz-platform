# API Contracts

این پوشه قرارداد رسمی ماشین‌خوان بین Backend و Frontend HamAmoz را نگهداری می‌کند.

## فایل‌ها

```text
contracts/openapi.yaml       Generated OpenAPI contract
contracts/API_CHANGELOG.md   Human-readable API change history
contracts/README.md          Contract ownership/workflow
```

## Snapshot فعلی

نسخه این Branch در تاریخ **2026-08-08** از `backend/comprehensive-manual-hardening` / PR #4 و commit زیر همگام شده است:

```text
c30d0a57d1d05c77b295797dae4e652295174e4e
```

`openapi.yaml` در این Branch همان Blob تولیدشده Feature Branch است و دستی بازنویسی نشده است.

## Source of Truth

ترتیب مرجع:

1. Backend code
2. tests/migrations
3. generated/live OpenAPI
4. committed `contracts/openapi.yaml`
5. docs

اگر generated schema با committed contract اختلاف دارد، Contract باید از Backend regenerate شود.

## تولید OpenAPI

در Repository کامل:

```bash
cd Backend
./scripts/generate_openapi.sh ../contracts/openapi.yaml
```

یا همان command پایه‌ای که CI اجرا می‌کند:

```bash
python manage.py spectacular \
  --api-version v1 \
  --file ../contracts/openapi.generated.yaml \
  --validate
```

سپس Diff باید review شود.

## ممنوعیت ویرایش دستی

این کار درست نیست:

```text
backend changed
-> manually patch openapi.yaml to look right
```

مسیر درست:

```text
backend changed
-> fix serializers/views/schema annotations
-> generate OpenAPI
-> validate
-> review diff
-> commit generated file
```

## چه تغییراتی نیاز به Regeneration دارند؟

- Endpoint
- HTTP Method
- Request body/schema
- Response body/schema
- Query parameter
- Path parameter
- Header parameter
- Authentication metadata
- Permission-visible contract behavior
- Status code
- Pagination
- Enum
- Nullability
- File upload/download MIME
- custom action schema

## Frontend Consumer Workflow

Frontend generated catalog:

```text
Frontend/src/api/generated/catalog.json
Frontend/src/api/generated/catalog.ts
```

تولید:

```bash
cd Frontend
npm run generate:api
```

Endpoint registry:

```text
Frontend/src/api/endpoints.ts
```

Application pageها باید Operation ID را از catalog/registry مصرف کنند و API path literal به `apiRequest` ندهند.

## CI Contract Drift

Backend CI:

```text
generate openapi.generated.yaml
-> validate
-> diff against contracts/openapi.yaml
```

Frontend CI:

```text
npm run generate:api
-> git diff --exit-code -- src/api/generated
```

بنابراین Backend schema و Frontend generated catalog نباید بدون commit هماهنگ از هم جدا شوند.

## تغییرات Contract مهم در Snapshot فعلی

### Comprehensive import only

Public create جدید فقط:

```text
import_type=comprehensive_school
```

Legacy typeهای `students`, `enrollments`, `scores`, `monthly_evaluations` برای Job تاریخی در Model باقی مانده‌اند، ولی create عمومی جدید آن‌ها را expose/accept نمی‌کند.

### Public template

فقط:

```http
GET /api/v1/imports/templates/comprehensive_school/
```

### Manual monthly evaluation

```http
GET    /api/v1/monthly-evaluations/catalog/
POST   /api/v1/monthly-evaluations/manual/
DELETE /api/v1/monthly-evaluations/{id}/manual/?reason=...
```

### Catalog

Contract شامل schema صریح برای:

- framework version
- score min/max
- metric count
- 74 metric definitions

### Manual evaluation input

```json
{
  "enrollment": "uuid",
  "month_no": 1,
  "note": "optional",
  "metrics": [
    {"metric_code": "EDU_01", "value": 4}
  ]
}
```

### Manual delete

`reason` یک query parameter required است و success response `204` دارد.

## Breaking Change Policy

Breaking change شامل مواردی مثل:

- حذف endpoint
- تغییر method
- required شدن field قبلاً optional
- حذف field
- تغییر type
- تغییر enum
- تغییر semantics status code
- تغییر permission/scope که client behavior را می‌شکند
- تغییر response structure

هر Breaking change باید در `API_CHANGELOG.md` ثبت شود و migration path داشته باشد.

Breaking change فعلی Import در Changelog ثبت شده است.

## API Change Changelog

فایل:

```text
contracts/API_CHANGELOG.md
```

برای هر Contract change حداقل مشخص شود:

- Added
- Changed
- Deprecated
- Removed
- Fixed
- Breaking Changes

## Test Contract

Backend regression tests برای schema جدید در:

```text
Backend/tests/test_openapi_schema.py
```

موارد فعلی:

- catalog 200 schema
- manual POST request schema
- manual POST 200/201 response schema
- manual DELETE reason parameter
- manual DELETE 204
- import create multipart request
- import enum restricted to `comprehensive_school`

## Validation Snapshot

آخرین Backend CI:

```text
OpenAPI errors: 0
OpenAPI warnings: 1
Committed contract diff: PASS
```

Warning فعلی مربوط به enum naming collision چند `status` field و generated component با نامی شبیه `Status6f2Enum` است. این Warning Contract validity را نمی‌شکند، ولی naming بهتر باید در follow-up با `ENUM_NAME_OVERRIDES` اصلاح شود.

## مسئولیت Backend

Backend owner باید:

1. behavior را در code enforce کند
2. permission/scope test اضافه کند
3. schema را regenerate کند
4. diff را review کند
5. changelog را update کند
6. breaking change را مشخص کند

## مسئولیت Frontend

Frontend باید:

1. committed OpenAPI را مصرف کند
2. generated catalog را sync نگه دارد
3. endpoint registry را از operation ID بسازد
4. typecheck/lint/test/build را اجرا کند
5. از hard-coded API assumptions جلوگیری کند

## فایل‌های مرتبط

- `../docs/FRONTEND_HANDOFF_FA.md`
- `../docs/CI_AND_CONTRACT_WORKFLOW_FA.md`
- `../docs/CURRENT_IMPLEMENTATION_2026-08-08_FA.md`
- `../docs/COMPREHENSIVE_IMPORT_AND_MANUAL_ENTRY_FA.md`
