# 23 — Production Readiness و گیت انتشار

## CI فعلی و F0

Backend CI شامل PostgreSQL 17، Redis، migration check، OpenAPI generation/validation/drift، Celery/Redis، MinIO/S3، coverage، backup/restore و image builds است. job اجباری `Integration Smoke` با Compose clean boot، health، login، dashboard، students، XLSX import و report preview در workflow ثبت شده است.

`scripts/docker-integration-smoke.sh` در پایان `docker compose down --volumes --remove-orphans` اجرا می‌کند. اجرای local Docker Desktop در 2026-08-10 green و cleanup آن خالی بود؛ نخستین green GitHub execution همچنان evidence لازم برای فعال‌کردن گیت remote است.

## مرز F8

کنترل‌های قابل version-control پیاده‌سازی شده‌اند: healthcheckهای Compose، clean-boot smoke، PostgreSQL restore drill، OpenAPI/Frontend contract gate، dashboardهای role-specific و runbookهای rollback. staging واقعی، protection شاخه در GitHub، rotation secret، offsite/PITR، WAF و pilot نیازمند credentials و اختیار محیط هستند و با کد محلی قابل «اجرا شده» تلقی نمی‌شوند.

## Runbook F0

1. clean clone و CI green.
2. Compose smoke green.
3. staging deploy با artifact SHA مشخص.
4. restore successful در محیط جداگانه.
5. pilot workflow و rollback rehearsal ثبت‌شده.

## Hardening پس از domainها

ترتیب: load test → profiling → indexes → monitoring → security hardening → DR.

security baseline: 2FA کارکنان حساس، session/device management، confidential-read audit، upload scanning، offsite backup/PITR، WAF و security alerts.

## Definition of Done

- tenant isolation، permissions، DB constraints، transitions، migrations، PostgreSQL tests.
- Backend/Frontend CI، OpenAPI/catalog sync، Docker smoke، docs/audit/PII logging review.
- staging acceptance و rollback path شناخته‌شده.
