# 15 — محدودهٔ محصول کامل و مرز معماری

## وضعیت

این سند معماری مصوب و وضعیت پیاده‌سازی را نشان می‌دهد. F1 تا F7 در کد، migration، API، Frontend و تست پیاده‌سازی شده‌اند؛ F8 نیز کنترل‌های منبع‌کد (CI، Compose smoke، مستندات و گیت‌های انتشار) را پوشش می‌دهد. اعمال تنظیمات remote مانند staging، branch protection، secret rotation و pilot همچنان عملیات مالک محیط است.

## معماری ثابت

```text
Browser TypeScript + esbuild
  -> Django REST API (/api/v1/)
  -> domain apps | selectors/read models | services/tasks
  -> PostgreSQL -> Redis/Celery -> filesystem/private S3
```

appهای افزوده‌شده: `behavior`, `activities`, `counseling`, `guidance`, `analytics`, `recommendations` و `portal`.

## تصمیم‌های خارج از scope

- microservice، React/Next migration، `Student360` model و generic event table.
- generic CRUD برای Counseling، DSL rule engine، AI-first recommendation و ABAC فراگیر.
- materialized view/cache/index حدسی پیش از اندازه‌گیری.

## ترتیب اجباری

F0 baseline → F1 Student 360 → F2 Behavior/Activities → F3 Counseling/Guidance → F4 Analytics → F5 Recommendations → F6 Reporting → F7 Portal → F8 hardening.

هر domain جدید باید `models`, `serializers`, `views`, `services`, `tasks`, `permissions`, `selectors`, `tests` و migration مناسب داشته باشد. مسیر دقیق و traceability در [مستندات محصول](../../docs/product/FULL_PRODUCT_ROADMAP_FA.md) است.
