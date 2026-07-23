# API Inventory (Legacy Pointer)

این فایل قبلاً Inventory مرحله ابتدایی پروژه بود و مسیرهایی مانند `auth/login/` و `health/` را نشان می‌داد که با API جاری سازگار نیستند.

برای قرارداد فعلی از منابع زیر استفاده کنید:

1. Schema زنده: `/api/v1/schema/`
2. Swagger: `/api/v1/docs/`
3. ReDoc: `/api/v1/redoc/`
4. راهنمای فارسی: `04-API_FA.md`
5. مرجع Attendance: `API_REFERENCE_FA.md`

Artifact قابل تحویل باید از همان Commit تولید شود:

```bash
./scripts/generate_openapi.sh build/openapi.yaml
```

فهرست کلی Resourceهای جاری:

```text
organizations, schools, academic-years, terms, grade-levels, classes
users, role-assignments
students, guardians, enrollments
subjects, grade-subjects, course-offerings
assessment-types, assessments, scores, calculation-policies
attendance-sessions, attendance-records, attendance-policies
attendance-alerts, parent-notifications, attendance-reports
imports, reports, dashboard
```
