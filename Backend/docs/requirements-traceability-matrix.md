# Backend MVP Requirements Traceability Matrix

| ID | Requirement | Planned slice | Verification |
|---|---|---:|---|
| MVP-INF-01 | Django/DRF modular monolith under `Backend/` | 0 | settings check, architecture review |
| MVP-INF-02 | PostgreSQL, Redis, Celery and object storage wiring | 0 | CI services, readiness, Docker smoke test |
| MVP-INF-03 | Custom user from first migration | 0 | migration and model/API tests |
| MVP-INF-04 | Versioned API, OpenAPI, standard errors and trace IDs | 0 | schema validation and API tests |
| MVP-ACC-01 | Organization, 13 schools, memberships and branch roles | 1 | model, API and permission tests |
| MVP-ACC-02 | Cross-branch isolation and IDOR prevention | 1+ | mandatory negative API tests per module |
| MVP-ACA-01 | Academic years, terms, grades and class sections | 2 | constraints and API tests |
| MVP-STU-01 | Student, guardian and annual enrollment history | 3 | model/service/API tests |
| MVP-STU-02 | Class change and transfer history | 3 | transactional service tests |
| MVP-CRS-01 | Subjects, grade subjects, offerings and teacher assignment | 4 | teacher-scope permission tests |
| MVP-SCR-01 | Assessments and bulk score entry | 5 | validation and API tests |
| MVP-SCR-02 | DRAFT/SUBMITTED/REJECTED/APPROVED/LOCKED workflow | 5 | state transition tests |
| MVP-SCR-03 | Locked-score override with mandatory reason and audit | 5 | service, permission and audit tests |
| MVP-CAL-01 | Decimal weighted averages, coefficients, pass and rank | 6 | deterministic calculation tests |
| MVP-CAL-02 | Formula versioning and reproducibility | 6 | regression and snapshot tests |
| MVP-IMP-01 | Atomic student, enrollment and score imports | 7 | rollback/idempotency tests |
| MVP-RPT-01 | RTL A4 individual and class PDF report cards | 8 | PDF generation and content tests |
| MVP-RPT-02 | Secure archived report download | 8 | permission and task idempotency tests |
| MVP-DSH-01 | Initial operational dashboard metrics | 9 | scoped aggregate API tests |
| MVP-AUD-01 | Initial audit logging and audit API | 9 | audit creation/access tests |
| MVP-OPS-01 | Backup, restore test, security and performance hardening | 10 | restore drill and regression suite |
| MVP-OPS-02 | Backend-only repository and CI | 0+ | path filters and changed-file review |
