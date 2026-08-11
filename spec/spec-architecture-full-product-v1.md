---
title: معماری محصول کامل هم‌آموز
version: 1.0
date_created: 2026-08-10
last_updated: 2026-08-10
owner: Product and Engineering
tags: [architecture, django, api, security, data, roadmap]
---

# Introduction

این specification قرارداد معماریِ توسعهٔ تدریجی هم‌آموز از MVP فعلی به محصول کامل است. مخاطب آن توسعه‌دهنده، reviewer و عامل‌های خودکار هستند. این سند جایگزین کد فعلی نیست؛ هر endpoint یا مدلِ target تا زمان پیاده‌سازی planned تلقی می‌شود.

## 1. Purpose & Scope

هدف: افزودن behavior، activities، counseling، guidance، analytics، recommendations، reporting platform و portal به معماری فعلی بدون تغییر معماری کلان یا شکستن قراردادهای موجود.

در scope:

- Production baseline با Compose clean boot و CI functional smoke.
- Student 360 به‌صورت read composition و lazy UI/API.
- domain model، state machine، authorization، migration، testing و documentation هر phase.

خارج از scope:

- microservices، React/Next migration، `Student360` model، generic event table، generic counseling CRUD، generic rule DSL، AI-first decision، ABAC engine فراگیر و Jinja/Python قابل‌اجرای مدیر.

## 2. Definitions

| اصطلاح | تعریف |
|---|---|
| Tenant | Organization که مرز اول isolation داده است. |
| Scope | Organization + School + object/cohort/relationship معتبر در سمت server. |
| Read composition | response/selectors فقط‌خواندنی که از domainهای موجود داده را ترکیب می‌کند و model جدید نمی‌سازد. |
| Private Note | متن مشاوره که فقط Counselor مجاز می‌تواند بخواند. |
| Evidence | ورودی ساختاریافته و قابل بازبینی که یک signal/recommendation را توجیه می‌کند. |
| Snapshot | داده و versionهای freeze‌شده برای بازتولید خروجی رسمی. |

## 3. Requirements, Constraints & Guidelines

- **REQ-001**: معماری باید Browser TypeScript application → Django REST API → domain/read/workflow → PostgreSQL/Redis-Celery/storage باقی بماند.
- **REQ-002**: Student 360 باید route فعلی `/students/:id` را توسعه دهد و فقط endpointهای کوچک lazy-load داشته باشد.
- **REQ-003**: Counseling نباید در response عمومی 360، dashboard غیرمجاز یا portal وجود داشته باشد.
- **REQ-004**: Behavior و Activity باید evidence مستقل از Monthly Evaluation باشند و نباید metric evaluation را خودکار تغییر دهند.
- **REQ-005**: هر risk signal باید `rule_code`, `rule_version`, `severity`, `evidence`, `explanation`, `window` داشته باشد.
- **REQ-006**: Recommendation باید audience-specific، deterministic، explainable و پیش از انتشار human-approved باشد.
- **REQ-007**: Report رسمی باید snapshot immutable از input و versionهای مرتبط داشته باشد.
- **REQ-008**: Parent/Student portal فقط relationshipهای server-derived را برای انتخاب Student بپذیرد.
- **SEC-001**: هر endpoint باید Organization، School، object scope و action permission را server-side بررسی کند.
- **SEC-002**: Private Note، متن جلسه و secret نباید در log، AuditEvent changes یا API غیرمجاز قرار گیرند.
- **SEC-003**: انتقال School نباید دسترسی خودکار به Counseling history بدهد؛ hand-off/referral صریح لازم است.
- **SEC-004**: break-glass در صورت پیاده‌سازی باید privilege، reason، request ID و audit metadata داشته باشد و متن confidential را ثبت نکند.
- **CON-001**: API additive زیر `/api/v1/` است و `contracts/openapi.yaml` دستی ویرایش نمی‌شود.
- **CON-002**: domainهای جدید از الگوی `models / serializers / views / services / tasks / permissions / selectors / tests` تبعیت می‌کنند.
- **CON-003**: هر record تاریخی FK مناسب، DB constraint، index مبتنی بر query، migration امن و transition صریح دارد.
- **GUD-001**: index فقط پس از evidence query/profiling اضافه می‌شود؛ index حدسی ممنوع است.
- **GUD-002**: UI pageها client call پراکنده ندارند و از `Frontend/src/api/`/catalog استفاده می‌کنند.
- **PAT-001**: analytics rule یک کلاس Python versioned است؛ `AnalyticsRuleConfig` فقط parameter را تغییر می‌دهد، algorithm را نه.

## 4. Interfaces & Data Contracts

### Current functional smoke contract

| Interaction | Method | Expected status | Assertion |
|---|---|---:|---|
| live/ready | GET `/api/v1/health/live/`, `/api/v1/health/ready/` | 200 | Compose dependency chain healthy |
| authenticate | POST `/api/v1/auth/token/` | 200 | access/refresh token returned |
| dashboard/students | GET `/dashboard/summary/`, `/students/` | 200 | authenticated/scoped read |
| comprehensive import | POST `/imports/` multipart | 201 then `completed` | valid XLSX reaches Celery workflow |
| report preview | POST `/reports/preview/` | 200 | snapshot has imported enrollment and rendered HTML |

### Target Student 360 contract

```text
GET /api/v1/students/{student_id}/360/summary/
GET /api/v1/students/{student_id}/360/academics/
GET /api/v1/students/{student_id}/360/attendance/
GET /api/v1/students/{student_id}/360/evaluations/
GET /api/v1/students/{student_id}/360/reports/
```

Target additions such as `behavior`, `activities`, `risks` and `recommendations` are individual lazy resources. Counseling uses a separate confidential API and is absent from this contract.

### Target risk signal example

```json
{
  "rule_code": "academic_drop",
  "rule_version": 1,
  "severity": "high",
  "evidence": {
    "subject": "math",
    "previous_average": 17.4,
    "current_average": 14.2,
    "drop": 3.2,
    "window_days": 45
  },
  "explanation": "Average dropped by 3.2 in the configured window.",
  "window": {"days": 45}
}
```

## 5. Acceptance Criteria

- **AC-001**: Given a clean runner, when `scripts/docker-integration-smoke.sh` runs, then it builds the Compose stack, completes the listed public contracts and removes containers and volumes.
- **AC-002**: Given a staff user without Counseling scope, when the user requests Student 360 or a portal response, then no private Counseling field is returned.
- **AC-003**: Given a student transfer, when a counselor in the target school reads old case data without referral, then the API denies access and records no confidential content in logs.
- **AC-004**: Given identical analytics fixture input and rule version, when the rule runs twice, then evidence and severity are identical and duplicate signal policy is deterministic.
- **AC-005**: Given a report archive snapshot, when current student/score data later changes, then the archived semantic snapshot remains unchanged.
- **AC-006**: Given a Parent account, when a client supplies another student ID, then the portal returns 403/404 according to the established non-disclosure policy and never returns another student’s data.

## 6. Test Automation Strategy

- **Unit**: domain state transitions, serializer validation, rule golden fixtures and snapshot construction.
- **Integration**: PostgreSQL-backed constraints, transaction rollback, duplicate/concurrent workflow operations and API authorization matrices.
- **End-to-End**: Compose script covers boot, health, login, dashboard, students, XLSX async import and report preview.
- **Contract**: `manage.py spectacular --validate`, diff against generated OpenAPI and frontend catalog generation/typecheck.
- **Security**: denied role, cross-organization, cross-school, cross-class, guide cohort, confidential read and portal IDOR tests.
- **Performance**: before adding indexes, capture query count/`EXPLAIN ANALYZE` on production-like data.

## 7. Rationale & Context

داده‌های دانش‌آموزی هم تاریخچه دارند و هم confidential boundaries. Read composition از duplication دانش‌آموز جلوگیری می‌کند. endpoint کوچک، lazy loading را ممکن و accidental data disclosure را دشوار می‌کند. ruleهای Python versioned قابل code review، golden-test و بازتولید هستند؛ DSL یا AI-first تصمیم‌گیری این قابلیت‌ها را تضعیف می‌کند. Snapshot گزارش نیز از بازنویسی تاریخ رسمی پس از تغییر دادهٔ جاری جلوگیری می‌کند.

## 8. Dependencies & External Integrations

### External Systems

- **EXT-001**: Browser/Nginx frontend — API proxy و application shell.

### Third-Party Services

- **SVC-001**: S3-compatible storage — private report/import artifact storage با authorization.

### Infrastructure Dependencies

- **INF-001**: PostgreSQL 17, Redis, Celery, Docker Compose and GitHub Actions.

### Data Dependencies

- **DAT-001**: Existing Organization/School/Enrollment/academic/evaluation/attendance/report data and official comprehensive XLSX template.

### Technology Platform Dependencies

- **PLT-001**: Django REST Framework, drf-spectacular, Python 3.12, TypeScript/esbuild and WeasyPrint remain platform choices.

### Compliance Dependencies

- **COM-001**: Organization policy must define retention, disclosure and emergency-access rules for Counseling before F3 production use.

## 9. Examples & Edge Cases

```text
Transfer A -> B:
  Enrollment may move to School B.
  Behavior/Guidance visibility follows its defined policy.
  Counseling private sessions from School A remain denied in School B.
  Only a recorded referral/handoff can release permitted shared information.

Parent portal:
  Client sends student_id=X.
  Server derives accessible students from Guardian -> StudentGuardian -> Student.
  If X is outside that set, server returns its established denied/not-found response.
```

## 10. Validation Criteria

1. `docker compose config --quiet` and `bash -n scripts/docker-integration-smoke.sh` exit 0.
2. The GitHub `integration-smoke` job has one green execution before F0 is accepted.
3. Generated OpenAPI equals the committed contract after any API change.
4. Each new domain has migration, DB constraints, permission tests, state-transition tests and documentation.
5. Staging/pilot/rollback evidence is attached before release gate closure.

## 11. Related Specifications / Further Reading

- [Full product roadmap](../docs/product/FULL_PRODUCT_ROADMAP_FA.md)
- [Requirements traceability](../docs/product/REQUIREMENTS_TRACEABILITY_FA.md)
- [Release plan](../docs/product/RELEASE_PLAN_FA.md)
- [Backend canonical index](../Backend/docs/00-INDEX_FA.md)
