# Complete Report Cards: Technical Design

## Scope and accepted product decisions

Deliver exactly seven independently selectable report layouts: `analytical_term_1`,
`analytical_term_2`, `analytical_annual`, `final_term_1`, `final_term_2`,
`final_annual`, and `summer_report`. Existing student and class report-card APIs,
templates, archives, portal access, and stored data remain backward compatible.

The repository is a Django/DRF modular monolith with a self-hosted Preact frontend.
`main` baseline is `48ea38ecf193bddc4f58a5b2720e9d423e06e28f`. Every historical
remote feature branch is behind that baseline; none has additional commits to reuse.
Only branch `feature/report-cards-complete` receives changes.

## Domain boundaries and rejected alternatives

1. Extend `hamamooz.apps.academics` with school/year-scoped report-card settings,
   settings revisions, weighted annual results, and class/grade/school dense ranks.
   This preserves the current ownership of educational rules and Decimal arithmetic.
2. Add `hamamooz.apps.summers` as an independent bounded context. Reusing `Term`,
   `CourseOffering`, `Assessment`, or ordinary `Score` was rejected because those
   models require ordinary class/term workflows and do not represent a single summer
   comprehensive exam with directly entered subject results.
3. Extend `hamamooz.apps.reports` for seven layout keys, safe period selection,
   immutable versioned approved snapshots, source fingerprints, family-safe data,
   Persian A4/A3 HTML/PDF templates, and editable RTL Word output. Replacing the
   existing WeasyPrint/docxtpl pipeline or introducing uploaded executable templates
   was rejected as unnecessary and unsafe.
4. Extend the existing central Preact API client and `/reports` surface. Mock-only
   management screens and a second disconnected frontend architecture are excluded.

## Academic results, precision, and ranking

`AcademicReportSettings` has one active configuration per school and academic year:
positive Decimal first/second term weights, independent class/grade/school rank
visibility switches, and a revision/version. `AcademicReportSettingsRevision`
captures actor, timestamp, school/year, previous values, replacement values, and a
reason; privileged updates also use the existing public audit mechanism.

Annual subject averages match the stable `GradeSubject` across first/second
term-specific offerings and use:

```text
(first_term_score * first_term_weight + second_term_score * second_term_weight)
/ (first_term_weight + second_term_weight)
```

The current school/year calculation policy controls Decimal rounding. The annual
overall average uses each grade-subject coefficient. Annual official issuance is
incomplete until both required term scores exist for every required subject; no
partial annual result is represented as a completed official result.

Existing `TermResult` gains grade/school ranks and cohort populations without
removing its current class rank. New `AnnualSubjectResult` and `AnnualResult`
persist annual results and all three dense ranks/populations. Cohorts are active
enrollments in exactly the same school and academic year; grade and class cohorts
add their respective scope filters. Equal Decimal averages share a rank; the next
distinct average increments the rank by one. Visibility changes affect presentation,
never the underlying stored calculation.

## Independent summer program

`SummerProgram` belongs to a school and academic year and has an optional Decimal
`pass_threshold` between 0 and 20. `SummerCourse` links the program to an existing
academic `Subject`. `SummerRegistration` links the program to a historical
`Enrollment`; its school and academic year must match the program. Student, grade,
and class identity are derived from that enrollment, not duplicated.

`SummerCourseRegistration` links one registration to one program course.
`SummerComprehensiveExam` belongs to the program. `SummerSubjectScore` links that
exam to one registered course and stores one Decimal score between 0 and 20.
Database uniqueness and cross-model validation prevent duplicate results and
cross-program combinations. The domain never stores questions, answer sheets,
correct/incorrect counts, negative marking, attendance, or invented summer ranks.

Threshold changes are captured by a dedicated revision and a public audit event.
Threshold `null` means no pass/fail state and no rendered status column. A summer
report is officially issuable only when its enrollment registration, exam state,
and every selected course score are valid and complete.

## Reports, snapshots, human approval, and privacy

Annual and summer drafts/archives support nullable `term`; legacy term-based rows
remain unchanged. A safe `period_type` and `period_label` eliminate assumptions
that `term.title` is always available. Summer reports reference their program.

Snapshots capture schema version, report family/layout, tenant/year/period,
enrollment or summer registration, identity and class/grade facts, subject scores,
averages, coefficients, fixed term weights, dense ranks/populations, fixed rank
visibility, optional threshold, approved family-facing recommendations, framework
version where available, a canonical SHA-256 source fingerprint, generation time,
approver, tracking code, and monotonically increasing archive version.

Draft creation can preview incomplete data with warnings. Submission, approval,
and rendering revalidate authoritative source completeness and fingerprint equality;
no direct archive endpoint or transition may bypass required human approval for
new official report families. Existing legacy report workflows are preserved.

Only explicitly approved presentation strings may be overridden: manager comment,
family recommendations, supplemental text, and a bounded display title/footer.
Identity, scores, averages, rank, school, year, pass state, and numeric weights
are never writable through report endpoints. Family-safe snapshots omit raw risk
signals, private counseling material, counselor/teacher/deputy/manager audiences,
unapproved recommendations, and expired recommendations.

The PDF is the archived official artifact; a separately generated editable DOCX
from the identical approved snapshot includes:

> نسخه قابل ویرایش — اعتبار نهایی با PDF آرشیوشده سامانه

Analytical documents use A3 landscape and server-generated data-backed SVG. Final
and summer documents use A4 portrait. All seven layouts use Persian RTL, the
repository's vendored Estedad/Vazirmatn fonts, school identity, navy/gold official
styling, tracking/version metadata, and signed/stamped official footers.

## API, frontend, security, and compatibility

New audited school-scoped settings, annual-result, summer-program/course/
registration/exam/score endpoints extend the existing DRF router. Explicit unsafe
action mappings authorize school managers and educational deputies; teachers and
operators receive only existing role-appropriate access. Querysets are tenant
scoped before object lookup and serializer/model validation rejects cross-school
relations and immutable-field mass assignment.

The real `/reports` Preact workspace loads students, academic years, terms,
settings, templates, archives, and summer data from existing/new API endpoints;
it creates previews/drafts, drives submit/approve/render, and links downloads.
The UI includes term weights, independent rank visibility, direct summer scores,
and optional threshold controls. Generated OpenAPI is updated only by the existing
schema-generation command when its runtime dependencies are available.

## Verification and honest environmental limits

Add focused pytest coverage before production changes for weighted arithmetic,
scope/isolation, equal-score dense ranking, optional thresholds, score ranges and
uniqueness, seven layouts, archive immutability/versioning/fingerprints, official
readiness, family-safe content, override rejection, and A4/A3/DOCX output.

At design time the local baseline has Python 3.12 and Node 24, but no installed
Django, DRF, pytest, WeasyPrint, docxtpl, Ruff, PostgreSQL, or Docker. The pinned
dependency install cannot use unavailable package-network access. Existing frontend
lint/build and all 11 Node tests pass; backend Python syntax compilation passes.
Runtime Django migrations/tests/PDF rendering must therefore be obtained from a
supported available environment or automatically triggered repository CI, and
must never be reported as executed if that evidence cannot be obtained.

## Acceptance ownership

- Academic agent: academic models/services/serializers/views/migration and tests.
- Summer agent: dedicated summers app/models/services/serializers/views/migration
  and summer tests.
- Reports agent: report models/services/serializers/views/migration, seven HTML
  layouts, SVG/Word support, and report/security tests.
- Frontend integrator: Preact report workspace, API adapter, frontend tests/style.
- Main integrator: Django app/router/settings wiring, shared docs/OpenAPI, focused
  and full verification, final independent review, commit/push and remote SHA proof.
