---
goal: Implement the approved HamAmoz full-product architecture without changing the modular-monolith platform
version: 1.0
date_created: 2026-08-10
last_updated: 2026-08-10
owner: Product and Engineering
status: 'In progress'
tags: [architecture, django, api, security, migration, ci]
---

# Introduction

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

This deterministic plan delivers the approved roadmap in deployable phases. F0 contains an implemented CI change that still requires its first green remote execution; later phases remain planned until their acceptance tests exist.

## 1. Requirements & Constraints

- **REQ-101**: Preserve the Browser TypeScript application, Django REST API, PostgreSQL, Redis/Celery and filesystem/S3 topology.
- **REQ-102**: Implement Student 360 as selectors and segmented read endpoints, never as a `Student360` model.
- **REQ-103**: Keep Counseling outside generic Student 360 and require a confidential permission boundary.
- **REQ-104**: Model Behavior/Activity facts separately from versioned Monthly Evaluation opinions.
- **REQ-105**: Implement Analytics and Recommendation as deterministic, versioned and explainable workflows.
- **REQ-106**: Build portal authorization from persisted Guardian/Student relationships rather than submitted student identifiers.
- **SEC-101**: Enforce organization, school, object and role/relationship checks in every new endpoint.
- **SEC-102**: Record confidential reads without confidential content and default-deny Counseling transfer.
- **CON-101**: Keep all additive HTTP interfaces below `/api/v1/`; generate OpenAPI and frontend catalog from code.
- **CON-102**: Use PostgreSQL-backed constraints, `PROTECT` history and explicit state transitions for new domains.
- **GUD-101**: Do not add performance indexes, cache layers or materialized views without measured query evidence.
- **PAT-101**: Place domain workflow logic in services/tasks and read composition in selectors, not views/pages.

## 2. Implementation Steps

### Implementation Phase 1 — F0 Production Baseline

- GOAL-101: Make Compose boot and a representative public workflow a required CI gate.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-101 | Keep `scripts/docker-integration-smoke.sh` as the only full-stack smoke entrypoint. It must build with `docker compose -p`, start isolated services, poll PostgreSQL/Redis/health endpoints, exercise token login, dashboard, students, valid comprehensive XLSX import, imported enrollment report preview, logout and `down --volumes`. | ✅ | 2026-08-10 |
| TASK-102 | Keep `.github/workflows/backend-ci.yml` path filters inclusive of `Backend/**`, `Frontend/**`, `docker-compose.yml` and the smoke script; run the `integration-smoke` job on push/PR to `main`. | ✅ | 2026-08-10 |
| TASK-103 | Run `integration-smoke` in GitHub Actions and attach the first successful run URL/check name to the release evidence. Do not mark F0 complete before it is green. |  |  |
| TASK-104 | Create staging inventory, rotation record, deployment target, rollback rehearsal and pilot evidence outside source control; link their identifiers in `docs/product/RELEASE_PLAN_FA.md`. |  |  |

### Implementation Phase 2 — F1 Student 360 v1

- GOAL-102: Transform the current student page into a permission-safe lazy read composition.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-105 | Add `Backend/hamamooz/apps/students/selectors.py` with `build_student_360_summary(student, request_scope)` and selectors for academics, attendance, evaluations and reports. Each selector must scope through visible Enrollment records. |  |  |
| TASK-106 | Add explicit actions/routes in `students/views.py` for `360/summary`, `academics`, `attendance`, `evaluations` and `reports`; update `config/api_urls.py`, tests and generated OpenAPI. Do not add Counseling data or a `Student360` model. |  |  |
| TASK-107 | Refactor `Frontend/src/pages/student.ts` and add `Frontend/src/components/student-360/` so each section lazy-loads through `Frontend/src/api/`; replace local interfaces with generated-contract-backed types where available. |  |  |

### Implementation Phase 3 — F2 Behavior and Activities

- GOAL-103: Add auditable event facts with constrained workflows.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-108 | Create `Backend/hamamooz/apps/behavior/` with BehaviorEventType, BehaviorEvent, BehaviorAction, BehaviorFollowUp and BehaviorAttachment. Add organization/school/year/enrollment ownership, indexes and DB constraints. |  |  |
| TASK-109 | Implement BehaviorEvent service transitions `draft -> confirmed -> under_follow_up -> resolved` and `draft|confirmed -> voided`; record revisions/audit after confirmation and prohibit direct Evaluation metric mutation. |  |  |
| TASK-110 | Create `Backend/hamamooz/apps/activities/` with Activity, ActivityParticipation, ActivityAchievement and ActivityAttachment. Support allowlisted kinds cultural, competition, research, sport, art and other. |  |  |
| TASK-111 | Add scoped serializers/views/permissions/selectors, migrations, PostgreSQL transition/constraint/concurrency tests, OpenAPI sync and lazy Student 360 sections for Behavior/Activities. |  |  |

### Implementation Phase 4 — F3 Counseling and Guidance

- GOAL-104: Add confidential Counseling and enrollment-bound guidance without cross-school leakage.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-112 | Add `COUNSELOR`, `GUIDE_TEACHER` and `STUDENT_AFFAIRS_DEPUTY` roles through an additive accounts migration and role tests. Preserve current six role semantics. |  |  |
| TASK-113 | Create `counseling` models/services/permissions/selectors for Case, Session, FollowUp, Referral, ActionPlan and Attachment. Store private/shared/released data in separately permissioned representations. |  |  |
| TASK-114 | Implement confidential-read audit fields actor, case/session ID, timestamp, reason, request ID and scope. Exclude session/note text from audit metadata and logs. |  |  |
| TASK-115 | Create `guidance` with GuideTeacherAssignment, GuideFollowUp and GuideActionPlan. Persist assignment to Enrollment with `starts_at` and `ends_at`; enforce cohort access server-side. |  |  |
| TASK-116 | Add transfer/referral tests proving that a target-school counselor cannot read source-school private history without explicit allowed hand-off. |  |  |

### Implementation Phase 5 — F4 Analytics and Risk

- GOAL-105: Produce deterministic and explainable risk signals from trusted domain data.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-117 | Create `analytics` models AnalyticsRuleConfig, AnalyticsRun, StudentRiskSignal and OperationalAlert with unique/idempotency constraints and evidence/version fields. |  |  |
| TASK-118 | Implement versioned Python rules under `analytics/rules/`: academic_drop_v1, multi_subject_drop_v1, high_unexcused_absence_v1, discipline_repeat_v1, performance_volatility_v1, peer_performance_drop_v1 and missing_teacher_scores_v1. |  |  |
| TASK-119 | Trigger targeted recomputation using `transaction.on_commit`; add a daily Celery Beat reconciliation task that detects and corrects missing/mismatched runs. |  |  |
| TASK-120 | Add golden fixtures asserting exact signal code/version/severity/evidence/window, duplicate-run behavior and scope-safe risk APIs. |  |  |

### Implementation Phase 6 — F5 Recommendations

- GOAL-106: Convert approved signals into reviewed, audience-specific recommendations.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-121 | Create `recommendations` models Recommendation and RecommendationDecision with one record per audience, reason snapshot, rule version, reviewer and timestamps. |  |  |
| TASK-122 | Implement states `draft -> pending_review -> approved|rejected` plus dismissed, expired and superseded paths; enforce idempotency and double-approval protection. |  |  |
| TASK-123 | Expose only approved/released records to the intended audience. Do not introduce AI-generated official decisions; any future rewrite remains human-reviewed. |  |  |

### Implementation Phase 7 — F6 Reporting Platform

- GOAL-107: Extend reports while preserving immutable official output semantics.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-124 | Add ReportTemplate and ReportDraft to `reports` with allowlisted block configuration, human-edit state and approval transitions. Do not execute administrator-supplied Jinja/Python. |  |  |
| TASK-125 | Expand snapshot builder to freeze allowed student, academics, attendance, evaluation framework, Behavior/Activity evidence, analytics signal/rule versions and approved recommendation text. |  |  |
| TASK-126 | Retain WeasyPrint for A4/A3 PDF; evaluate `docxtpl` only when editable Word report requirements are accepted and dependency policy passes. |  |  |
| TASK-127 | Add snapshot reproducibility tests and report permission tests for draft, submit, approve, render and archive actions. |  |  |

### Implementation Phase 8 — F7 Parent and Student Portal

- GOAL-108: Expose a deliberately limited relationship-authorized portal.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-128 | Add GuardianAccount and StudentAccount or equivalent persisted relation models; derive visible children/students server-side for every portal request. |  |  |
| TASK-129 | Add PortalVisibilityPolicy with report=released, recommendations=approved_only, attendance_summary=visible, behavior=hidden, counseling=never and guide_plan=released_only defaults. |  |  |
| TASK-130 | Add portal API/frontend views for my children, child switch, released reports, approved recommendations, follow-up plans, notification acknowledgement and consent/privacy. |  |  |
| TASK-131 | Add Parent/Student IDOR, cross-student, cross-school, visibility and confidential-Counseling denial E2E tests. |  |  |

### Implementation Phase 9 — F8 Product Hardening

- GOAL-109: Measure, secure and operate completed domain workflows.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-132 | Profile production-like workflows using query count and `EXPLAIN ANALYZE`; add only evidence-backed indexes and document query plans. |  |  |
| TASK-133 | Add monitoring, sensitive-staff 2FA/session management, upload scanning, offsite backup/PITR, WAF/security alert requirements and disaster-recovery rehearsal evidence. |  |  |
| TASK-134 | Run a production-readiness review against all Definition of Done gates and publish release notes/pilot outcome. |  |  |

## 3. Alternatives

- **ALT-101**: Microservices — rejected because current scale benefits from Django transactions and lower deployment complexity.
- **ALT-102**: A `Student360` persistence model — rejected because it duplicates source domains and increases consistency risk.
- **ALT-103**: Generic event table or programmable rule DSL — rejected because explicit models/rules are safer to migrate, review and test.
- **ALT-104**: React/Next migration — rejected because current TypeScript/esbuild router/application shell already satisfies the target and migration adds regression cost.
- **ALT-105**: AI-first recommendation decision — rejected because official advice must remain deterministic, explainable and human-approved.

## 4. Dependencies

- **DEP-101**: Existing Organization, School, Student, Enrollment, academic, attendance, evaluation, import and report models remain the source data.
- **DEP-102**: PostgreSQL 17, Redis, Celery and S3-compatible storage must remain available in CI/staging.
- **DEP-103**: drf-spectacular/OpenAPI contract generation and Frontend catalog generation are required for all API additions.
- **DEP-104**: Staging target, GitHub protection policy, secret inventory and pilot dataset require repository/product-owner authorization.

## 5. Files

- **FILE-101**: `scripts/docker-integration-smoke.sh` — isolated Compose public-contract E2E script.
- **FILE-102**: `.github/workflows/backend-ci.yml` — required backend/Compose smoke workflow.
- **FILE-103**: `Backend/hamamooz/apps/students/{selectors.py,views.py,serializers.py,tests/}` — F1 read composition implementation.
- **FILE-104**: `Backend/hamamooz/apps/{behavior,activities,counseling,guidance,analytics,recommendations}/` — future bounded apps and migrations.
- **FILE-105**: `Backend/hamamooz/apps/reports/` — reporting draft/template/snapshot extension.
- **FILE-106**: `Frontend/src/pages/` and `Frontend/src/components/` — lazy domain UI using generated API contracts.
- **FILE-107**: `Backend/docs/` and `docs/product/` — canonical documentation and ADR traceability.

## 6. Testing

- **TEST-101**: Execute `bash -n scripts/docker-integration-smoke.sh` and `docker compose config --quiet` before CI submission.
- **TEST-102**: Execute GitHub `integration-smoke` and preserve its first green evidence before closing F0.
- **TEST-103**: Add PostgreSQL domain tests for state transitions, constraints, rollback and concurrent duplicate operations in every new app.
- **TEST-104**: Add authorization matrices for role, organization, school, class/cohort, counseling scope and portal relationship.
- **TEST-105**: Add OpenAPI drift and frontend generated-catalog checks for every interface change.
- **TEST-106**: Add golden analytics and immutable report snapshot fixture tests.

## 7. Risks & Assumptions

- **RISK-101**: The smoke relies on seed fixture values `branch-01`, `1405-1406`, `7-a` and `first`; changes to `seed_demo` must update the script atomically.
- **RISK-102**: Bash/WSL may lack Docker Desktop integration. The local fallback `DOCKER_BIN=docker.exe` was verified, but the first GitHub CI execution remains required evidence.
- **RISK-103**: Counseling implementation without an approved retention/visibility policy risks confidential data leakage.
- **RISK-104**: Portal work before relationship and visibility policy tests creates IDOR risk.
- **ASSUMPTION-101**: GitHub Ubuntu runners provide Docker Compose, curl and Python 3 used by the smoke script.
- **ASSUMPTION-102**: Current private S3 and backup drills remain part of Backend CI while the new smoke uses filesystem storage in its isolated Compose project.

## 8. Related Specifications / Further Reading

- [Architecture specification](../spec/spec-architecture-full-product-v1.md)
- [Full product roadmap](../docs/product/FULL_PRODUCT_ROADMAP_FA.md)
- [Requirements traceability](../docs/product/REQUIREMENTS_TRACEABILITY_FA.md)
- [Release plan](../docs/product/RELEASE_PLAN_FA.md)
- [Backend documentation index](../Backend/docs/00-INDEX_FA.md)
