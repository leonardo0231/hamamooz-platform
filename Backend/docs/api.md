# API Inventory

All routes are under `/api/v1/`.

## Implemented in Slice 0

| Method | URL | Authentication | Purpose |
|---|---|---|---|
| POST | `/auth/login/` | Public | Obtain access and refresh JWTs |
| POST | `/auth/refresh/` | Refresh token | Rotate refresh token |
| POST | `/auth/verify/` | Token payload | Verify JWT |
| POST | `/auth/logout/` | Bearer JWT | Blacklist refresh token |
| GET | `/auth/me/` | Bearer JWT | Current user profile |
| POST | `/auth/change-password/` | Bearer JWT | Change current password |
| GET | `/health/` | Public | Liveness probe |
| GET | `/readiness/` | Public | Database/cache readiness |
| GET | `/schema/` | Public | OpenAPI schema |
| GET | `/docs/` | Public | Swagger UI |
| GET | `/redoc/` | Public | ReDoc |

## Planned MVP route groups

`users`, `roles`, `memberships`, `organizations`, `schools`, `academic-years`, `terms`, `grade-levels`, `class-sections`, `students`, `guardians`, `enrollments`, `subjects`, `grade-subjects`, `course-offerings`, `teacher-assignments`, `assessment-types`, `assessments`, `scores`, `calculations`, `imports`, `reports`, `dashboard-metrics`, and `audit-logs`.

Sensitive workflow transitions will use explicit action endpoints rather than generic updates.
