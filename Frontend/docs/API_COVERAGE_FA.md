# پوشش API در Frontend

Catalog تولیدشده از قرارداد رسمی شامل **164 Operation** و **142 Schema** است.

| Tag | عملیات | روش‌ها | مصرف UI |
|---|---:|---|---|
| `academic-years` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `assessment-types` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `assessments` | 12 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `attendance-alerts` | 5 | GET, POST | Alert Center |
| `attendance-policies` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `attendance-records` | 7 | GET, POST | Generic Resource Page و Schema-driven Actions |
| `attendance-reports` | 4 | GET, POST | Generic Resource Page و Schema-driven Actions |
| `attendance-sessions` | 10 | DELETE, GET, PATCH, POST, PUT | Attendance Page |
| `auth` | 4 | GET, POST | Login، Session Recovery، Refresh، Me و Logout |
| `calculation-policies` | 3 | GET, POST | Generic Resource Page و Schema-driven Actions |
| `classes` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `course-offerings` | 7 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `dashboard` | 1 | GET | Dashboard |
| `enrollments` | 6 | GET, POST | Generic Resource Page و Schema-driven Actions |
| `grade-levels` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `grade-subjects` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `guardians` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `health` | 2 | GET | Generic Resource Page و Schema-driven Actions |
| `imports` | 4 | GET, POST | Imports Page |
| `organizations` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `parent-notifications` | 3 | GET, POST | Generic Resource Page و Schema-driven Actions |
| `reports` | 5 | GET, POST | Reports Page |
| `role-assignments` | 6 | DELETE, GET, PATCH, POST, PUT | Roles Page |
| `schools` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `scores` | 3 | GET, POST | Generic Resource Page و Schema-driven Actions |
| `students` | 7 | DELETE, GET, PATCH, POST, PUT | Student List و Student Detail |
| `subjects` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `terms` | 6 | DELETE, GET, PATCH, POST, PUT | Generic Resource Page و Schema-driven Actions |
| `users` | 7 | GET, PATCH, POST, PUT | Users Page |

## Endpointهای حیاتی

```text
POST /api/v1/auth/token/
GET /api/v1/auth/me/
POST /api/v1/auth/token/refresh/
POST /api/v1/auth/logout/
GET /api/v1/organizations/
GET /api/v1/schools/
GET /api/v1/dashboard/summary/
GET /api/v1/students/
GET /api/v1/attendance-alerts/
POST /api/v1/attendance-alerts/evaluate/
POST /api/v1/imports/
POST /api/v1/reports/
```

تمام Pathها از Operation IDهای `contracts/openapi.yaml` در `src/api/endpoints.ts` یا مستقیماً از Catalog تولیدشده resolve می‌شوند. تست خودکار تضمین می‌کند صفحات، Componentها و App Layer هیچ Endpoint literal به `apiRequest` ندهند. برای Actionهایی که Schema خودکار DRF با Serializer واقعی View ناسازگار بود، `src/api/action-schemas.ts` فقط Payloadهای تأییدشده از کد Backend را Override می‌کند و این تطبیق با تست قرارداد پوشش داده شده است.
