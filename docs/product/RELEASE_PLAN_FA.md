# برنامهٔ انتشار و گیت‌های عملیاتی

## مدل کار

هر branch حداکثر 1 تا 3 روز کار دارد و پس از PR و CI به `main` squash-merge می‌شود. نمونه‌ها:

```text
feat/behavior-foundation
feat/behavior-events-api
feat/behavior-frontend
feat/activities-foundation
feat/activities-frontend
feat/student360-behavior
```

`main` باید در تمام زمان‌ها deployable بماند؛ phase چندماهه به یک branch واحد تبدیل نمی‌شود.

## گیت F0

| گیت | فرمان/شاهد | مالک وضعیت |
|---|---|---|
| Compose configuration | `docker compose config --quiet` | CI |
| image build | `docker build` Backend و Frontend | CI |
| functional clean boot | `bash scripts/docker-integration-smoke.sh` | CI `integration-smoke` |
| backend quality/contract/restore | `Backend CI` | CI |
| frontend catalog/typecheck/lint/test/build | `Frontend CI` | CI |
| staging deploy | محیط staging و URL | [ASK USER] |
| secret inventory/rotation | inventory و rotation record | [ASK USER] |
| rollback rehearsal | timestamp و نتیجهٔ rehearsal | [ASK USER] |
| pilot workflow | dataset غیرتولیدی و UAT record | [ASK USER] |

## تنظیم پیشنهادی main

```text
no force push
no delete
pull request required
required checks: Backend CI, Frontend CI, Integration Smoke
squash merge preferred
```

تنظیم remote GitHub از repository source قابل اثبات نیست؛ تا زمانی که مالک repository آن را اعمال نکرده، این مورد یک requirement عملیاتی باز است.

## Staging checklist

1. secrets خارج از repository و inventory با owner/rotation-date ثبت شوند.
2. config staging با production از نظر host/CORS/storage/worker/backup مقایسه شود.
3. deploy از artifact commit SHA انجام شود و health live/ready ثبت گردد.
4. restore به محیط جداگانه آزمایش و دادهٔ حساس پاک‌سازی شود.
5. pilot با dataset مجاز اجرا، UAT ثبت و rollback trigger توافق شود.

## معیار rollback

- migration مخرب یا ناسازگار، breach scope، شکست سلامت پایدار یا data-integrity failure trigger است.
- rollback باید شامل image قبلی، migration-safe policy و restore path آزموده‌شده باشد؛ حذف داده برای rollback مجاز نیست.
