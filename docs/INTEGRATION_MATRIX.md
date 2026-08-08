# ماتریس یکپارچه‌سازی Backend و Frontend

Snapshot: **2026-08-08** — مبنا: `backend/comprehensive-manual-hardening` / PR #4 / `c30d0a57...`.

این جدول «وجود و اتصال واقعی در source + تست/CI» را ثبت می‌کند. ستون QA به معنی پذیرش دستی محصول نیست مگر صریح نوشته شود.

| جریان | Endpoint / Route | Contract | Backend | Frontend | Validation |
|---|---|---|---|---|---|
| Login | `POST /api/v1/auth/token/` | Ready | Implemented | Integrated | Frontend auth tests + CI pass |
| Current user | `GET /api/v1/auth/me/` | Ready | Implemented | Integrated | Session restore tested |
| Logout | `POST /api/v1/auth/logout/` | Ready | Implemented | Integrated | Auth flow tested |
| Organization/School scope | `/organizations/`, `/schools/` + scope headers | Ready | Scoped | Integrated | Access/security tests pass |
| Dashboard | `/api/v1/dashboard/...` | Ready | Implemented | Integrated | Critical endpoint tests pass |
| Comprehensive template | `GET /api/v1/imports/templates/comprehensive_school/` | Ready | Implemented | Integrated | Backend API test pass |
| Comprehensive upload | `POST /api/v1/imports/` | Ready | `comprehensive_school` only | Integrated | Backend + frontend contract tests pass |
| Import history/status | `GET /api/v1/imports/` | Ready | Scoped | Integrated | CI pass |
| Import retry | `POST /api/v1/imports/{id}/retry/` | Ready | Implemented | Integrated | Workflow tests pass |
| Import cancel | `POST /api/v1/imports/{id}/cancel/` | Ready | Implemented | Integrated | Workflow tests pass |
| Import errors | `GET /api/v1/imports/{id}/errors/` | Ready | XLSX output | Integrated | API path covered |
| Manual entry hub | `/manual-entry` | N/A UI route | Uses domain APIs | Implemented | typecheck/lint/test/build pass |
| Generic manual create | Domain `POST` operations | Generated | Existing domain validation | Schema form integrated | Generated catalog + registry tests pass |
| Monthly evaluation catalog | `GET /api/v1/monthly-evaluations/catalog/` | Ready | Implemented | Integrated | OpenAPI + frontend registry pass |
| Monthly evaluation upsert | `POST /api/v1/monthly-evaluations/manual/` | Ready | Scoped + transactional | Integrated | create/update/scope regression tests pass |
| Monthly evaluation delete | `DELETE /api/v1/monthly-evaluations/{id}/manual/` | Ready | Soft-delete + audit | Integrated | delete/reason/audit tests pass |
| Enrollment transitions | Dedicated change-class/transfer/status actions | Existing contract | Domain workflow preserved | Existing management flow | Backend invariant tests pass |
| OpenAPI generation | `contracts/openapi.yaml` | Generated | CI generated | Consumed | drift check pass |
| Frontend API catalog | `Frontend/src/api/generated/*` | From OpenAPI | N/A | Generated | drift check pass |

## Status Definitions

### Ready

Path/method/schema در OpenAPI Commit‌شده وجود دارد و CI generated diff را پاس می‌کند.

### Implemented

Behavior در source Backend وجود دارد و صرفاً Contract placeholder نیست.

### Scoped

Query/write scope در Backend اعمال می‌شود؛ مخفی کردن UI معیار امنیت نیست.

### Integrated

Frontend source واقعاً عملیات را از API client/endpoint registry مصرف می‌کند.

### Validation pass

آخرین CI بررسی‌شده سبز بوده است؛ این معادل Manual QA کامل محصول نیست.

## آخرین Validation

Backend:

```text
Run 31248852083
137 passed
coverage 80.08% >= 78%
OpenAPI errors 0
```

Frontend:

```text
Run 31248852078
21 passed
0 failed
typecheck/lint/build pass
```

## Breaking Change فعلی

Public bulk importهای زیر برای create جدید دیگر Contract عمومی نیستند:

```text
students
enrollments
scores
monthly_evaluations
```

مسیر جدید:

```text
comprehensive_school
```

برای single entry از Domain API / `/manual-entry` استفاده می‌شود. Historical ImportJobها حذف نشده‌اند.

## قواعد به‌روزرسانی این Matrix

- تغییر Contract بدون regenerate OpenAPI مجاز نیست.
- وضعیت Frontend فقط با وجود consumer واقعی در source تغییر کند.
- `CI pass` را با `manual QA accepted` یکی نکنید.
- Scope/permission باید با Backend test تأیید شود.
- هر Breaking Change باید به `contracts/API_CHANGELOG.md` وصل شود.
