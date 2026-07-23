# امنیت، حریم خصوصی و کنترل دسترسی

## مدل نقش

| نقش | Scope | اختیارات اصلی |
|---|---|---|
| `system_admin` | کل سامانه | همه مجموعه‌ها و شعب |
| `organization_admin` | مجموعه | ساختار مشترک و همه شعب مجموعه |
| `school_manager` | شعبه | کاربر و عملیات شعبه |
| `educational_deputy` | شعبه | آموزش، review، lock و اصلاح رسمی |
| `operator` | شعبه | ورود داده، ثبت‌نام و Import |
| `teacher` | شعبه + درس/کلاس | ارزیابی، نمره و حضور زنگ خودش |

یک کاربر می‌تواند در شعب مختلف نقش متفاوت داشته باشد. مدیریت نقش سلسله‌مراتبی است؛ مدیر شعبه نمی‌تواند مدیر سیستم، مدیر مجموعه یا نقش شعبه دیگر را مدیریت کند.

## الگوریتم Tenant isolation

1. JWT هویت کاربر فعال را تعیین می‌کند.
2. RoleAssignmentهای فعال، مجموعه‌ها و شعب مجاز را می‌سازند.
3. Header انتخابی parse و با Scope مجاز intersect می‌شود.
4. QuerySet فقط داده Scope مجاز را برمی‌گرداند.
5. برای Write، action باید mapping نقش صریح داشته باشد؛ نبود mapping به معنی deny است.
6. پس از Save نیز object permission داخل همان transaction دوباره بررسی می‌شود.
7. Service invariantهای مقصد، teacher ownership و سازگاری روابط را کنترل می‌کند.

Read خارج از Scope معمولاً 404 می‌شود، چون شیء وارد QuerySet نمی‌شود. Header نامعتبر یا Write خارج Scope پاسخ 403 دارد.

## احراز هویت

- Access token کوتاه‌عمر و Refresh token چرخشی
- blacklist پس از rotation و Logout
- revoke Refresh tokenها در تغییر رمز و غیرفعال‌سازی کاربر
- Login با username یا email
- Rate limit سخت‌تر برای Login
- `UPDATE_LAST_LOGIN` برای ثبت آخرین ورود

## کنترل داده و فایل

- statusها، actorها و فیلدهای workflow از mass assignment محافظت می‌شوند.
- مقدار نمره با Decimal و constraint غیرمنفی کنترل می‌شود.
- Import فقط XLSX با محدودیت حجم، ردیف، ستون، اندازه uncompressed و compression ratio است.
- تصویر حداکثر ۲ MiB و Attendance evidence با محدودیت تک‌فایل/مجموع و signature کنترل می‌شود.
- S3 objectها private و URLها امضاشده‌اند.
- سرو فایل محلی و PDF renderer به MEDIA_ROOT محدود می‌شوند تا traversal رخ ندهد.
- Antivirus یا content disarm در MVP وجود ندارد.

## Audit و Log

- ورود موفق/ناموفق، Logout، CRUD مهم، انتقال، workflow نمره، Attendance، Import و Report Audit می‌شوند.
- Request ID در log و پاسخ وجود دارد.
- Audit changes فقط فیلدهای غیرحساس را نگه می‌دارد.
- فیلدهایی مانند password، national ID، phone، email، address، note، reason و recipient redacted می‌شوند.
- Sentry با `send_default_pii=False` فعال می‌شود.
- اعتماد به `X-Forwarded-For` فقط با `TRUST_X_FORWARDED_FOR=true` انجام می‌شود.

## سخت‌گیری Production

Settings production در startup خطا می‌دهد اگر:

- `DJANGO_SECRET_KEY` کوتاه یا placeholder باشد.
- `DJANGO_ALLOWED_HOSTS` خالی یا شامل `*` باشد.
- Database غیر PostgreSQL یا password آن placeholder باشد.
- S3 فعال ولی credential معتبر نباشد.
- SMTP فعال ولی `EMAIL_HOST` خالی باشد.
- تعداد تلاش Notification کمتر از یک باشد.

همچنین Secure Cookie، HSTS، `X_FRAME_OPTIONS=DENY`، content-type nosniff و SSL proxy header فعال‌اند.

## نکات عملیاتی

1. Secretها و `.env` نباید Commit شوند.
2. TLS باید در Load Balancer یا Nginx بیرونی terminate شود.
3. Admin بهتر است فقط از VPN/IP مدیریتی در دسترس باشد.
4. PostgreSQL، Redis و MinIO API نباید مستقیم روی اینترنت منتشر شوند.
5. بکاپ باید رمزگذاری و off-host شود؛ Volume همان Host کافی نیست.
6. Snapshot گزارش، Audit و فایل‌های عذر داده شخصی‌اند و Retention/Access policy می‌خواهند.
7. CORS، CSRF و Allowed Hosts باید فقط دامنه‌های واقعی را شامل شوند.

## Threat matrix

| تهدید | کنترل فعلی | ریسک باقی‌مانده |
|---|---|---|
| تغییر UUID برای مشاهده شعبه دیگر | Query scope + object check | نیاز به تست نفوذ مستقل |
| نوشتن بدون Tenant صریح | fail-closed RolePermission | Client باید header صحیح بفرستد |
| دبیر روی درس دیگر | teacher ownership | خطای پیکربندی RoleAssignment |
| تغییر status مستقیم | read-only fields + service transition | endpoint جدید باید mapping صریح داشته باشد |
| تغییر نمره پس از lock | correction جدا + reason + revision | سوءاستفاده reviewer باید با monitoring کشف شود |
| Import نیمه‌کاره | validate-all + transaction | فایل بزرگ هنوز بار CPU ایجاد می‌کند |
| فایل مخرب | signature/size/extension | Antivirus وجود ندارد |
| اعلان تکراری | dedupe + claim/idempotency | gateway بیرونی باید idempotency را رعایت کند |
| دستکاری گزارش تاریخی | Snapshot + formula version | حفاظت storage و backup لازم است |

## خارج از Baseline

2FA، WebAuthn، مدیریت session/device، Field-level encryption، WAF، Antivirus، PITR، SIEM کامل، Audit همه Readها و Data Loss Prevention در این MVP پیاده‌سازی نشده‌اند.
