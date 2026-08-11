# گزارش خوانش کدبیس و ممیزی baseline نقشه‌راه

- تاریخ: 2026-08-10
- روش: اسکن `docs/codebase/.codebase-scan.txt`، خوانش مستقیم workflow/Compose/API/models/routes و بررسی static contract.
- runtime evidence: `DOCKER_BIN=docker.exe bash scripts/docker-integration-smoke.sh` در Docker Desktop محلی با exit 0 اجرا شد؛ container/volume/temp directory باقی نماند.

## زمینهٔ تصمیم

- تصمیم پشتیبانی‌شده: آیا roadmap می‌تواند بدون تغییر معماری فعلی اجرا شود؟ نتیجه: بله؛ gapهای F0 عملیاتی‌اند، نه نیازمند تغییر platform.
- مخاطب: توسعه‌دهندهٔ اصلی، reviewer و مالک release.
- Driver: Codex شواهد source را خواند و تغییر حداقلی CI/documentation را اعمال کرد. Navigator: کاربر/مالک repository برای staging، protection و policyهای خارج از source.
- افق: F0 تا F8؛ این گزارش وضعیت source در تاریخ بالا را می‌سنجد، نه وضعیت live production.

## پرونده‌های خوانده‌شده و شواهد

| حوزه | پرونده‌های نمونه | نتیجهٔ قابل اتکا |
|---|---|---|
| CI | `.github/workflows/backend-ci.yml`, `frontend-ci.yml` | PostgreSQL 17، Redis، OpenAPI drift، S3/backup و build موجودند؛ Compose E2E قبلاً نبود. |
| Compose | `docker-compose.yml`, `Backend/Dockerfile` | `db`, Redisها، release/bootstrap, web, worker, beat و frontend تعریف و healthcheck شده‌اند. |
| API | `Backend/config/api_urls.py`, `config/urls.py` | API جاری `/api/v1/` است و endpointهای 360/new domain هنوز ثبت نشده‌اند. |
| دانش‌آموز/Frontend | `students/views.py`, `Frontend/src/pages/student.ts`, `Frontend/src/app/routes.ts` | route `/students/:id` موجود است؛ page هنوز local interfaces دارد. |
| Evaluation/Reports | `evaluations/catalog.py`, models, `reports/services.py` | 74 metric versioned و ReportArchive snapshot/formula version موجود است. |
| Import/Smoke | `imports/serializers.py`, `views.py`, `comprehensive.py`, `seed_demo.py` | import فقط XLSX جامع می‌پذیرد؛ seed یک School/Class/Term دارد ولی دانش‌آموز ندارد. |

## نتیجهٔ ممیزی

| ادعا | وضعیت | توضیح |
|---|---|---|
| معماری فعلی با modular monolith هم‌راستاست | تأیید | هیچ microservice یا frontend framework migration لازم نیست. |
| CI پایهٔ مهمی دارد | تأیید | workflow Backend و Frontend خوانده و شواهد فوق مشاهده شد. |
| Docker build به‌تنهایی کافی نیست | تأیید | job پیشین فقط `docker compose config` و image build داشت. |
| smoke جدید public contract را می‌سنجد | تأیید محلی؛ CI gate باز | script health, auth, dashboard, students, valid XLSX async import, report preview و cleanup را با exit 0 اجرا کرد. |
| staging/protection/rotation/pilot در source وجود دارد | تأیید نشده | configuration remote/operational در repository پیدا نشد؛ [ASK USER]. |

## تغییرات حاصل از ممیزی

- `scripts/docker-integration-smoke.sh` اضافه شد و job `integration-smoke` به Backend CI افزوده شد.
- path filters PR برای Compose، Frontend و script جدید پوشش داده شد.
- نقشه‌راه، traceability، glossary، specification، implementation plan و ADRها canonical می‌شوند.

## مناطق خوانده‌نشده یا نیازمند تأیید عملیاتی

- تنظیم واقعی GitHub branch protection و environment secrets.
- deployment target و کیفیت staging/production data.
- نخستین GitHub Actions execution از job `integration-smoke`؛ local Docker Desktop green است اما CI evidence هنوز ثبت نشده است.

## Action log

| اقدام | مالک | trigger بازبینی | وابستگی | وضعیت |
|---|---|---|---|---|
| اجرای workflow جدید و ثبت نتیجهٔ runtime | CI/repository owner | نخستین PR/push | GitHub-hosted Docker | باز |
| اعمال main protection | repository owner [ASK USER] | پیش از F0 exit | GitHub admin access | unknown |
| ایجاد و مستندسازی staging | operations owner [ASK USER] | پیش از pilot | deployment target | unknown |
| تأیید secret rotation | security/operations owner [ASK USER] | پیش از staging | secret inventory | unknown |
