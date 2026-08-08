# مستندات HamAmoz

این پوشه Snapshot مستندات یکپارچه‌سازی و وضعیت فنی پروژه را نگهداری می‌کند.

## Snapshot جاری

```text
Date: 2026-08-08
Feature branch: backend/comprehensive-manual-hardening
PR: #4
Head: c30d0a57d1d05c77b295797dae4e652295174e4e
```

## ترتیب مطالعه پیشنهادی

1. [`../README.md`](../README.md) — نمای کلی معماری، وضعیت، اجرای محلی، امنیت و CI
2. [`CURRENT_IMPLEMENTATION_2026-08-08_FA.md`](CURRENT_IMPLEMENTATION_2026-08-08_FA.md) — Snapshot دقیق تغییرات جاری و فایل‌های تحت تأثیر
3. [`COMPREHENSIVE_IMPORT_AND_MANUAL_ENTRY_FA.md`](COMPREHENSIVE_IMPORT_AND_MANUAL_ENTRY_FA.md) — فایل جامع، identity، upsert، manual entry و delete policy
4. [`FRONTEND_HANDOFF_FA.md`](FRONTEND_HANDOFF_FA.md) — قرارداد اجرایی Frontend/Backend و endpoint registry
5. [`CI_AND_CONTRACT_WORKFLOW_FA.md`](CI_AND_CONTRACT_WORKFLOW_FA.md) — تست، CI، OpenAPI و generated catalog
6. [`INTEGRATION_MATRIX.md`](INTEGRATION_MATRIX.md) — وضعیت integration جریان‌های کلیدی
7. [`API_CHANGE_TEMPLATE.md`](API_CHANGE_TEMPLATE.md) — قالب ثبت تغییر API
8. [`DOCKER_LOCAL_FA.md`](DOCKER_LOCAL_FA.md) — راهنمای Docker محلی
9. [`DOCKER_REVIEW_FA.md`](DOCKER_REVIEW_FA.md) — نکات Review محیط Docker

## Contract

فایل‌های Contract در:

```text
../contracts/openapi.yaml
../contracts/API_CHANGELOG.md
../contracts/README.md
```

`openapi.yaml` generated output است و نباید دستی ویرایش شود.

## Source of Truth

در اختلاف اطلاعات:

```text
code
> tests/migrations
> generated/live OpenAPI
> contracts/openapi.yaml
> architecture docs
> README
> assumptions
```

## نکته درباره این Branch

این Branch مستندات را با Feature Branch جدید همگام کرده است، اما وجود یک Feature در این Snapshot به معنی Merge شدن آن به `main` نیست. وضعیت Merge باید از PR/branch جاری بررسی شود.
