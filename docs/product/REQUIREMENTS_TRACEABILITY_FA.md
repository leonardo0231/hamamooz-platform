# ردیابی نیازمندی‌های محصول کامل

ستون Status فقط وضعیت مشاهده‌شده در source یا وضعیت برنامه‌ریزی‌شده را بیان می‌کند؛ `implemented` یعنی کد، migration و تست مربوط در همین repository وجود دارد، اما گیت‌های remote/staging فقط با evidence محیط مقصد complete می‌شوند.

| ID | نیازمندی | Source/Evidence | Domain | API یا سطح تحویل | Test/verification | Status |
|---|---|---|---|---|---|---|
| RQ-001 | modular monolith حفظ شود | `docker-compose.yml`, ADR-0001 | همه | `/api/v1/` | architecture review | accepted |
| RQ-002 | Frontend RTL مبتنی بر Preact با build تکرارپذیر و بدون CDN اجرا شود | `Frontend/package.json`, `Frontend/src/vendor/`, `Frontend/scripts/build.mjs` | frontend | route/application shell | lint + test + production build | implemented |
| RQ-003 | OpenAPI از Backend تولید شود | `backend-ci.yml`, `contracts/README.md` | API | `contracts/openapi.yaml` | generate + diff | existing |
| RQ-004 | PostgreSQL/Redis/Celery/S3/backup CI | `backend-ci.yml` | platform | CI | workflow jobs | existing |
| RQ-005 | Compose clean boot و functional smoke | `scripts/docker-integration-smoke.sh` | platform | health/auth/dashboard/import/report preview | local run + GitHub workflow | implemented (remote evidence pending) |
| RQ-006 | staging، rotation، protection و pilot | source workflow ندارد | platform | deployment/process | checklist + rehearsal | planned |
| RQ-007 | Student 360 read composition | `students/selectors.py`, `student.ts` | students | `/students/{id}/360/*` | selector/API/UI/security tests | implemented |
| RQ-008 | counseling از 360 عمومی خارج باشد | counseling views + Student 360 selectors | counseling | API جدا و capability-protected | denied payload tests | implemented |
| RQ-009 | 74 metric در 9 حوزه | `evaluations/catalog.py` | evaluations | monthly evaluations | catalog/model tests | existing |
| RQ-010 | Behavior state/audit | `behavior` app | behavior | behavior events/actions/follow-ups | transition/audit tests | implemented |
| RQ-011 | Activity/participation model | `activities` app | activities | activities/participations | validation/scope tests | implemented |
| RQ-012 | Counselor private note boundary | `counseling` app | counseling | confidential endpoints | security threat tests | implemented |
| RQ-013 | Guidance به Enrollment و بازه متصل شود | `guidance` app | guidance | assignments/follow-ups | transfer/cohort tests | implemented |
| RQ-014 | transfer confidential data default-deny | counseling referral service | counseling/guidance | referral/handoff only | cross-school denial | implemented |
| RQ-015 | Rules deterministic/versioned/explainable | `analytics/rules` | analytics | risk signals/config/runs | golden fixtures | implemented |
| RQ-016 | target task + nightly reconciliation | analytics scheduling/tasks | analytics | on_commit + Celery Beat | idempotency/reconciliation tests | implemented |
| RQ-017 | Recommendation human-approved/audience-specific | `recommendations` app | recommendations | recommendation/decision | state/visibility tests | implemented |
| RQ-018 | Official report snapshot immutable | `reports/models.py`, `reports/services.py` | reports | ReportArchive | snapshot reproducibility | existing foundation |
| RQ-019 | template allowlist، نه Jinja دلخواه | ReportTemplate + services | reports | ReportTemplate blocks | injection/allowlist tests | implemented |
| RQ-020 | Parent/Student relationship-based auth | GuardianAccount/StudentAccount | portal | `/portal/*` | IDOR/relationship tests | implemented |
| RQ-021 | released-only portal visibility | PortalVisibilityPolicy | portal/reports | visibility policy | cross-audience tests | implemented |
| RQ-022 | role-specific dashboards | dashboard role views | dashboard | `/dashboard/<role>/` | scope/query tests | implemented |
| RQ-023 | no PII in log/audit text | `core/services.py` redaction + roadmap | core/counseling | logging/audit | logging inspection tests | partially existing |
| RQ-024 | safe migrations and rollback | app migrations + backup drill | every new app | migration plan | migrate/rollback/restore drill | implemented (remote restore rehearsal pending) |

هر PR باید rowهای متاثر را با مسیر API/test واقعی به‌روزرسانی کند.
