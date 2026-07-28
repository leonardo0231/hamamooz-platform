# گزارش بازبینی Backend

تاریخ بازبینی: 2026-07-23

دامنه: ساختار `Backend/` در شاخه `backend/mvp-bootstrap`، شامل کد Django/DRF، مدل‌ها، Serviceها، Taskها، تست‌ها، Settings، Compose، اسکریپت‌ها و مستندات.

> یادداشت وضعیت 2026-07-26: این فایل Snapshot تاریخی بازبینی 2026-07-23 است.
> بعد از آن Backend CI اضافه شد و کنترل‌های Runtime محلی اجرا شدند: ۹۱ تست موفق،
> یک تست PostgreSQL روی SQLite رد شد، Ruff و Django check موفق بودند و قرارداد
> OpenAPI با خروجی تولیدشده برابر بود. نتیجه جاری و فاصله محصول در
> `../../docs/PRODUCT_COMPLETION_REVIEW_2026-07-26_FA.md` ثبت شده است.

## جمع‌بندی

معماری برای مقیاس MVP مناسب و نسبتاً منسجم است. نقاط قوی اصلی، Scope چندلایه، fail-closed بودن actionهای ناامن، Enrollment تاریخ‌مند، workflow رسمی نمره، استفاده از Decimal، Import اتمیک، Snapshot گزارش، Attendance مبتنی بر Enrollment و جداسازی Redis cache/broker هستند.

ریسک اصلی مشاهده‌شده در زمان بازبینی، **ناهمگامی مستندات و artifactهای API با کد جاری** بود، نه یک نقص قطعی runtime. بدون اجرای dependencyها و suite روی PostgreSQL نمی‌توان سلامت نهایی Runtime را تضمین کرد.

## نقاط قوت

| حوزه | مشاهده |
|---|---|
| معماری | مرز دامنه‌ها روشن و Service layer برای mutationهای مهم وجود دارد |
| Tenant isolation | Query، permission، object check، serializer و service چندلایه‌اند |
| امنیت write | action بدون role mapping صریح deny می‌شود |
| تاریخچه | EnrollmentEvent، ScoreRevision، AttendanceRecordRevision و Audit وجود دارند |
| هم‌زمانی | transaction و `select_for_update` در مسیرهای حساس استفاده شده است |
| محاسبات | Decimal، Policy نسخه‌دار و Snapshot رسمی |
| Async | queue تفکیک‌شده، on-commit، retry و idempotency در Jobهای اصلی |
| عملیات | release job، user غیر root، health، backup و storage profile |
| تست | ۸۴ تابع تست در حوزه‌های API، security، concurrency، report و attendance |

## یافته‌های مستندات

### High: Schemaهای static با کد جاری همگام نیستند

- `docs/openapi-schema.yml` routeهای قدیمی مانند `auth/login/` دارد.
- `openapi.yaml` مسیرهای Attendance را ندارد و برای Enrollment عملیات PUT/PATCH/DELETE نشان می‌دهد، در حالی که ViewSet جاری فقط GET/POST و actionهای دامنه را مجاز می‌کند.
- منبع حقیقت باید Schema تولیدشده از همان Commit باشد.

اقدام: منبع حقیقت و دستور generation در README، نمایه، API، تست و manifest شفاف شد. حذف یا regenerate artifactهای tracked باید در PR جدا و همراه dependency کامل انجام شود.

### Medium: تعارض دامنه Attendance

سند Scope قدیمی، Attendance را هم پیاده‌سازی‌شده و هم خارج MVP معرفی می‌کرد.

اقدام: Scope به «Attendance کامل در Backend با محدودیت کانال والد» اصلاح شد و فقط پنل والد و قابلیت‌های پیشرفته خارج MVP ماندند.

### Medium: توصیف استقرار قدیمی

سند Operations، Migration را داخل entrypoint و Redis را یک سرویس معرفی می‌کرد؛ Compose جاری از `release` یک‌بارمصرف و دو Redis جدا استفاده می‌کند.

اقدام: service map، release flow، profile S3 و backup serviceها مطابق Compose بازنویسی شد.

### Medium: دستورهای Offline قدیمی

نام serviceها و imageهای Bundle با Compose جاری سازگار نبودند.

اقدام: راهنمای offline با image tag، override بدون build و serviceهای واقعی بازنویسی شد.

### Low: چند منبع موازی و legacy

اسناد شماره‌دار فارسی، فایل‌های انگلیسی قدیمی، گزارش‌های تاریخی و دو Schema static کنار هم وجود دارند.

اقدام: `00-INDEX_FA.md` ترتیب منبع حقیقت و وضعیت legacy را تعیین کرد. فایل قدیمی حذف نشد.

## یافته‌های عملیاتی باقی‌مانده

| اولویت | مورد | اثر | پیشنهاد |
|---:|---|---|---|
| Medium | Backend CI اضافه شده ولی Run موفق متناظر در GitHub مشاهده نشد | سلامت CI راه دور هنوز اثبات نشده است | Push/PR و بررسی PostgreSQL + Ruff + Pytest + OpenAPI diff |
| Medium | `purge_expired_files` schedule داخلی ندارد | رشد storage | CronJob/systemd timer |
| Medium | dispatch دوره‌ای notification recovery در Beat نیست | ماندن Jobهای آماده retry | Scheduler جدا |
| Medium | Metrics exporter وجود ندارد | تشخیص دیرهنگام degradation | Prometheus/OpenTelemetry |
| Medium | backup در Volume محلی است | از دست‌رفتن همراه Host | نسخه رمزگذاری‌شده off-host |
| Medium | Antivirus فایل وجود ندارد | ریسک فایل مخرب | scan gateway/quarantine |
| Low | `coverage.xml` tracked و تاریخی است | برداشت اشتباه از کیفیت Commit جاری | تولید فقط به‌عنوان CI artifact یا regenerate |
| Low | branch coverage threshold ندارد | مسیرهای شرطی کم‌پوشش ممکن است بمانند | threshold تدریجی |

## بررسی‌های انجام‌شده

موفق:

```text
compile تمام Pythonهای config/hamamooz/tests
parse pyproject.toml
parse docker-compose.yml
syntax تمام scripts/*.sh
استخراج استاتیک route، action، model، constraint، role mapping و test inventory
```

اجرا نشد:

```text
Django system checks
Ruff
Pytest
OpenAPI generation تازه
PDF rendering
PostgreSQL concurrency tests
```

علت: dependencyهای پروژه در محیط بازبینی نصب نبودند. هیچ ادعای pass برای این کنترل‌ها ثبت نمی‌شود.

## اولویت اقدام بعدی

1. راه‌اندازی CI با PostgreSQL و generate/diff OpenAPI.
2. regenerate یا حذف کنترل‌شده Schemaهای static قدیمی در PR جدا.
3. زمان‌بندی retention و notification recovery.
4. اجرای Load test با ۱۳ شعبه، ثبت هم‌زمان نمره/حضور، Import ۵۰۰۰ ردیفی و report گروهی.
5. restore drill و ثبت RPO/RTO.
6. تست نفوذ Scope، upload و Admin قبل از داده واقعی.
