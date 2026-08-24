# Complete Analytical, Final, and Summer Report Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development to
> implement domain-isolated tasks; use dispatching-parallel-agents only where file
> ownership does not overlap. Steps use checkbox syntax for tracking.

**Goal:** Deliver seven approved, versioned, privacy-safe Persian RTL report cards
with weighted annual academics, three independently configurable ranks, an
independent direct-score summer program, real management UI, and editable Word.

**Architecture:** Preserve the repository's Django/DRF modular monolith. Extend the
existing academics/reports bounded contexts and Preact API adapter; add one
dedicated summers app linked to historical Enrollment. The main integrator owns
shared settings/router/contract files to avoid concurrent edits.

**Tech Stack:** Python 3.12, Django 5.2.16, DRF 3.16.0, Decimal, PostgreSQL/SQLite,
pytest, WeasyPrint, docxtpl/python-docx, Preact/HTM, Node built-in test runner.

## Global Constraints

- Only branch `feature/report-cards-complete`; never modify `main` or open a PR.
- Preserve all existing reports, APIs, comments, user files, and historical data.
- Exactly seven layout keys: `analytical_term_1`, `analytical_term_2`,
  `analytical_annual`, `final_term_1`, `final_term_2`, `final_annual`,
  `summer_report`.
- Positive Decimal term weights; inclusive 0..20 Decimal summer scores/thresholds.
- First/second terms are mandatory for complete annual official issuance.
- Active enrollment cohorts are scoped to school and academic year; ranks are dense.
- Managers and educational deputies own settings, approval, and issuance.
- Never expose counseling notes, raw risk evidence, internal or expired advice.
- A4 portrait for final/summer; A3 landscape for analytical; real editable DOCX.
- Use test-first development; record exact checks and explicitly name blocked ones.
- Main integrator exclusively owns `Backend/config/api_urls.py`,
  `Backend/config/settings/base.py`, `contracts/openapi.yaml`, and shared fixtures.

---

### Task 1: Preserve verified codebase knowledge and accepted design

**Files:**
- Modify: `docs/codebase/ARCHITECTURE.md`
- Modify: `docs/codebase/CONCERNS.md`
- Modify: `CONTEXT.md`
- Create: `docs/superpowers/specs/2026-08-24-report-cards-complete-design.md`
- Create: `docs/superpowers/plans/2026-08-24-report-cards-complete.md`

**Interfaces:**
- Consumes: verified `main` SHA, branch ancestry, repo docs, existing domain models.
- Produces: accepted glossary, feature design, file ownership, evidence-backed plan.

- [ ] Check `git branch -a -vv` and compare all historical remote branch ancestry.
- [ ] Read repo instructions, CI, existing architecture, reports, security, and tests.
- [ ] Document existing report bypass/privacy risks and independent summer boundary.
- [ ] Preserve all seven existing evidence-backed `docs/codebase` documents.

### Task 2: Weighted annual calculations, audit history, and three dense ranks

**Files:**
- Create: `Backend/tests/test_annual_report_cards.py`
- Modify: `Backend/hamamooz/apps/academics/models.py`
- Modify: `Backend/hamamooz/apps/academics/calculations.py`
- Modify: `Backend/hamamooz/apps/academics/serializers.py`
- Modify: `Backend/hamamooz/apps/academics/views.py`
- Modify: `Backend/hamamooz/apps/academics/admin.py`
- Create: `Backend/hamamooz/apps/academics/migrations/0005_report_card_academics.py`

**Interfaces:**
- Consumes: `Enrollment`, `Term.Code.FIRST/SECOND`, `GradeSubject.coefficient`,
  `SubjectResult`, `TermResult`, `get_policy`, `quantize`, existing audit/RBAC.
- Produces: `AcademicReportSettings`, `AcademicReportSettingsRevision`,
  `AnnualSubjectResult`, `AnnualResult`, `get_academic_report_settings(school,
  academic_year)`, `calculate_enrollment_annual(enrollment)`,
  `recalculate_school_term(school, term)`,
  `recalculate_school_annual(school, academic_year)`,
  `AcademicReportSettingsViewSet`, and `AnnualResultViewSet`.

- [ ] Write failing tests for `(15*1 + 18*2)/3 == Decimal('17.00')`, equal and
  decimal weights, invalid nonpositive weights, lesson coefficients, missing terms,
  manager/deputy mutation, unauthorized mutation, school/year separation, revision
  snapshots, three cohort population counts, and dense ties.
- [ ] Add school/year settings with two positive Decimal weights, three independent
  visibility switches, revision counter, actor-aware revision records and DB checks.
- [ ] Add persistent annual subject/results and three rank/population result fields.
- [ ] Implement stable subject matching across term offerings and policy rounding.
- [ ] Recalculate class, grade, and school ranks from same-school/year active
  enrollments; retain existing legacy class-rank behavior and contracts.
- [ ] Implement tenant-scoped audited DRF settings/result serializers and viewsets.
- [ ] Generate or hand-review a standard additive migration; compile changed files.
- [ ] Run `pytest -q tests/test_annual_report_cards.py` when dependencies exist;
  otherwise record why this exact runtime check is blocked.

### Task 3: Independent summer courses, registration, comprehensive exam, scores

**Files:**
- Create: `Backend/tests/test_summer_program.py`
- Create: `Backend/hamamooz/apps/summers/__init__.py`
- Create: `Backend/hamamooz/apps/summers/apps.py`
- Create: `Backend/hamamooz/apps/summers/models.py`
- Create: `Backend/hamamooz/apps/summers/services.py`
- Create: `Backend/hamamooz/apps/summers/serializers.py`
- Create: `Backend/hamamooz/apps/summers/views.py`
- Create: `Backend/hamamooz/apps/summers/admin.py`
- Create: `Backend/hamamooz/apps/summers/migrations/__init__.py`
- Create: `Backend/hamamooz/apps/summers/migrations/0001_initial.py`

**Interfaces:**
- Consumes: `School`, `AcademicYear`, `Enrollment`, `academics.Subject`, scoped
  roles/querysets, existing `record_audit` and Decimal validation.
- Produces: `SummerProgram`, `SummerProgramRevision`, `SummerCourse`,
  `SummerRegistration`, `SummerCourseRegistration`, `SummerComprehensiveExam`,
  `SummerSubjectScore`, `summer_registration_result(registration, exam=None)`,
  `validate_summer_report_readiness(registration, exam=None)`, and six audited
  DRF viewsets for program/course/registration/course-registration/exam/score.

- [ ] Write failing tests for program/year scoping, enrollment identity, unique
  registered courses, exam uniqueness, direct Decimal scores, 0/20 boundaries,
  rejected negative/>20 values, duplicate score, optional threshold, threshold
  revision, no pass state at null, incomplete course roster, and cross-school access.
- [ ] Implement independent models with `PROTECT`, scoped uniqueness, check
  constraints and `clean()` cross-program/school/year invariants.
- [ ] Add school-manager/deputy-authorized CRUD, teacher/operator-safe scope rules,
  direct score entry, audited threshold updates and readiness services.
- [ ] Derive optional pass status and weighted mean only from existing valid course
  coefficients, never from answers, questions, negative marking or invented ranks.
- [ ] Prepare and inspect the additive initial migration; compile changed files.
- [ ] Run `pytest -q tests/test_summer_program.py` if the runtime is available.

### Task 4: Seven layouts, immutable official snapshots, approval and safe exports

**Files:**
- Create: `Backend/tests/test_report_cards_complete.py`
- Modify: `Backend/hamamooz/apps/reports/models.py`
- Modify: `Backend/hamamooz/apps/reports/services.py`
- Modify: `Backend/hamamooz/apps/reports/serializers.py`
- Modify: `Backend/hamamooz/apps/reports/views.py`
- Modify: `Backend/hamamooz/apps/reports/admin.py`
- Create: `Backend/hamamooz/apps/reports/migrations/0003_complete_report_cards.py`
- Create: `Backend/templates/reports/includes/report_base.html`
- Create: `Backend/templates/reports/includes/report_identity.html`
- Create: `Backend/templates/reports/includes/report_signatures.html`
- Create: `Backend/templates/reports/analytical_term_1.html`
- Create: `Backend/templates/reports/analytical_term_2.html`
- Create: `Backend/templates/reports/analytical_annual.html`
- Create: `Backend/templates/reports/final_term_1.html`
- Create: `Backend/templates/reports/final_term_2.html`
- Create: `Backend/templates/reports/final_annual.html`
- Create: `Backend/templates/reports/summer_report.html`

**Interfaces:**
- Consumes: academic settings/results and summer registration/readiness interfaces
  from Tasks 2-3, plus existing `ReportArchive`, `ReportDraft`, `ReportTemplate`.
- Produces: nullable-safe term/summer period metadata; `REPORT_CARD_TEMPLATE_KEYS`;
  family-safe immutable snapshot/version/tracking/source fingerprint; seven HTML
  selectors; official PDF and editable RTL DOCX generation and secure transitions.

- [ ] Write failing tests for every layout key, term/annual/summer scope, archive
  version/tracking, stale fingerprints, required locked scores, approved human
  transition, archived stability after weight/score change, rank switches, denied
  overrides, internal/expired advice filtering, raw-risk exclusion, optional summer
  status-column removal, A4/A3 page size, server-rendered SVG and editable DOCX.
- [ ] Extend report types/period selection additively and keep legacy APIs working.
- [ ] Add version/tracking/program fields and null-safe `period_label`; freeze all
  semantically required facts and canonical SHA-256 fingerprints at approval.
- [ ] Enforce completeness/fingerprint checks at submit, approve, and render; do not
  permit new official families through a direct archive bypass.
- [ ] Allow only harmless approved plain-text presentation overrides; scope archive
  snapshots to authorized roles and hide sensitive product context from family.
- [ ] Add seven independently structured navy/gold RTL printable HTML templates,
  data-backed server-side SVG charts, and optional summer status column.
- [ ] Generate official WeasyPrint PDF and a genuinely editable RTL DOCX with the
  required nonofficial notice and equivalent selected snapshot content.
- [ ] Run focused report/privacy/export tests where dependencies are available.

### Task 5: Register APIs and implement a real Preact report-card workspace

**Files:**
- Modify: `Backend/config/settings/base.py`
- Modify: `Backend/config/api_urls.py`
- Modify: `Frontend/src/core/api.js`
- Modify: `Frontend/src/main.js`
- Create: `Frontend/src/pages/reports.js`
- Modify: `Frontend/src/styles/pages.css`
- Create: `Frontend/tests/reports.test.mjs`
- Modify: `contracts/API_CHANGELOG.md`
- Generate: `contracts/openapi.yaml` only via `Backend/scripts/generate_openapi.sh`.

**Interfaces:**
- Consumes: Task 2 settings/annual viewsets, Task 3 summer viewsets, Task 4 reports
  templates/drafts/archive actions, existing Preact hooks/store/API client.
- Produces: registered authenticated `/api/v1/academic-report-settings/`,
  `/annual-results/`, `/summer-programs/`, `/summer-courses/`,
  `/summer-registrations/`, `/summer-course-registrations/`, `/summer-exams/`,
  `/summer-subject-scores/`, and an operational Preact `/reports` management page.

- [ ] Add Node tests proving `/reports` is a real page rather than GenericPage, all
  seven layouts are selectable, and API adapters call authenticated scoped paths.
- [ ] Register only the summers app and approved viewsets in shared integration
  files after domain-agent changes have settled.
- [ ] Implement live loading of students/terms/templates/archives/settings/summer
  records; controls for layout/period, weight/rank settings, threshold/course
  scores, draft/submit/approve/render and archived downloads.
- [ ] Preserve demo behavior only as explicit existing demo mode; production paths
  always use the centralized authenticated scope-aware API adapter.
- [ ] Run `node scripts/lint.mjs`, `node --test`, `node scripts/build.mjs`.
- [ ] Generate OpenAPI only if Django and required plugins are available; otherwise
  explicitly record that contract regeneration was blocked.

### Task 6: Independent review, verification, delivery and remote proof

**Files:**
- Review: all task-owned files and additive migrations.
- Modify: only files required to address verified review findings.

**Interfaces:**
- Consumes: clean task diffs, exact test output, repository GitHub Actions jobs.
- Produces: verified feature-branch commit SHA and exact GitHub branch status.

- [ ] Dispatch an independent security/spec reviewer. Inspect cross-school IDOR,
  teacher/operator privilege, family snapshot leakage, migration dependencies,
  legacy compatibility and report-issued data immutability.
- [ ] Run `python -m compileall -q config hamamooz tests`, focused/full pytest,
  migration check, Ruff, frontend lint/tests/build, PDF/DOCX visual generation and
  schema regeneration when the actual environment allows each operation.
- [ ] Inspect `git diff --check`, `git diff --stat`, tracked-file scope, and secret
  exposure before creating an authorized feature-branch commit.
- [ ] Push `feature/report-cards-complete` without force and inspect remote branch
  SHA plus any automatically triggered GitHub Actions checks/logs.
- [ ] Report exact main SHA, final commit, changed files, migrations, test evidence,
  PDF/Word verification limits, checkout and repository-specific deployment steps.
