# Backend MVP Requirements

## Product boundary

The backend owns data modeling, business workflows, API security, imports, calculations, reports, asynchronous jobs, internal administration, audit, deployment and technical documentation. A user interface is outside this repository's scope.

## MVP scope summary

1. Multi-branch organization and 13 schools.
2. Custom users, school memberships and branch-scoped roles.
3. Students, guardians and annual enrollments.
4. Academic years, terms, grades, classes, subjects, offerings and teachers.
5. Assessments, bulk score entry, approval and locking workflow.
6. Versioned Decimal-based calculation engine.
7. Atomic Excel imports for students, enrollments and scores.
8. RTL A4 individual and class PDF report cards with secure archive/download.
9. Initial dashboard metrics and audit API.
10. حضور و غیاب روزانه و زنگ، توجیه غیبت، هشدار و اعلان والدین.
11. PostgreSQL، Redis، Celery، object storage، OpenAPI، Docker، CI، backup و restore verification.

## Explicitly outside MVP

Behavior، فعالیت‌های فرهنگی، soft skills، مشاوره کامل، پنل مستقل والد/دانش‌آموز، تحلیل سه‌ساله، توصیه هوشمند، Word، A3 و گزارش‌ساز کاربرمحور. پیامک فقط از طریق backend قابل‌پیکربندی ارائه می‌شود.
