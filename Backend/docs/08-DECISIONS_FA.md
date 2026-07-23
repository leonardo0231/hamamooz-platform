# تصمیم‌های معماری

## ADR-001: Django + DRF

وضعیت: پذیرفته‌شده

CRUD و Relation زیاد، Admin، Permission، ORM و سرعت توسعه برای سامانه مدرسه، Django 5.2 و DRF 3.16 را مناسب می‌کند.

## ADR-002: Modular Monolith به‌جای Microservice

وضعیت: پذیرفته‌شده

۱۳ شعبه و چند هزار دانش‌آموز نیازمند پیچیدگی شبکه و consistency توزیع‌شده نیست. تراکنش ثبت‌نام، نمره و حضور در یک DB ساده‌تر و قابل اتکاتر است.

## ADR-003: Shared database با Scope صریح

وضعیت: پذیرفته‌شده

گزارش مشترک مجموعه نیازمند داده یکپارچه است. Tenant isolation در Query، permission، serializer و service اعمال می‌شود.

## ADR-004: Enrollment تاریخ‌مند

وضعیت: پذیرفته‌شده

Student به Class متصل نمی‌شود. Enrollment رابطه Student + School + Year + Grade + Class را با بازه زمانی نگه می‌دارد و تغییر کلاس/انتقال را بدون حذف سابقه ممکن می‌کند.

## ADR-005: Decimal و Policy نسخه‌دار

وضعیت: پذیرفته‌شده

Float برای نمره رسمی مناسب نیست. محاسبات Decimal هستند، Policy از Scope خاص به عمومی resolve می‌شود و نسخه روی Result/Report ثبت می‌شود.

## ADR-006: Workflow در سطح Assessment

وضعیت: پذیرفته‌شده

Review معمولاً کل دفتر نمره یک آزمون را پوشش می‌دهد. اصلاح استثنایی Score قفل‌شده Assessment را Unlock نمی‌کند.

## ADR-007: Import تمام یا هیچ

وضعیت: پذیرفته‌شده

قالب ثابت است و کل فایل قبل از Write validate می‌شود. یک خطا کل Job را fail می‌کند تا reconciliation دستی لازم نشود.

## ADR-008: PDF همراه Snapshot

وضعیت: پذیرفته‌شده

فایل به‌تنهایی برای Audit کافی نیست. JSON داده، نسخه فرمول و PDF کنار هم آرشیو می‌شوند.

## ADR-009: UUID عمومی

وضعیت: پذیرفته‌شده

UUID ادغام/تفکیک سرویس آینده را آسان و enumeration را سخت‌تر می‌کند، اما جایگزین Authorization نیست.

## ADR-010: ML/AI خارج MVP

وضعیت: پذیرفته‌شده

تا تثبیت داده تاریخی و فرایند انسانی، تحلیل هوشمند می‌تواند گمراه‌کننده باشد.

## ADR-011: Attendance بر پایه Enrollment

وضعیت: پذیرفته‌شده

AttendanceRecord به Enrollment متصل است، نه Student/Class مستقیم؛ بنابراین انتقال و تغییر کلاس، معنای رکورد تاریخی را تغییر نمی‌دهد.

## ADR-012: Outbox و idempotency برای اعلان

وضعیت: پذیرفته‌شده

ارسال خارجی داخل transaction دامنه انجام نمی‌شود. ParentNotification وضعیت، attempts، dedupe و claim دارد تا retry و failure قابل کنترل باشد.

## ADR-013: Migration در release job

وضعیت: پذیرفته‌شده

Migration و collectstatic در سرویس یک‌بارمصرف اجرا می‌شوند. web و worker بدون side effect startup بالا می‌آیند و replicaها هم‌زمان schema را تغییر نمی‌دهند.

## ADR-014: Redis جدا برای Cache و Broker

وضعیت: پذیرفته‌شده

Cache می‌تواند eviction داشته باشد، اما Broker نباید پیام را بر اثر فشار حافظه حذف کند. دو Redis با policy متفاوت استفاده می‌شود.

## ADR-015: Schema پویا منبع حقیقت API

وضعیت: پذیرفته‌شده

Schema باید از code همان Commit تولید شود. فایل static بدون کنترل freshness فقط artifact تحویل است و canonical محسوب نمی‌شود.

## ADR-016: Soft delete برای دامنه، append-only برای تاریخچه

وضعیت: پذیرفته‌شده

داده عملیاتی قابل غیرفعال‌سازی است، اما Audit، revision، event و Snapshot برای حفظ سابقه فیزیکی حذف نمی‌شوند.
