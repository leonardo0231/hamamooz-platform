# امنیت، حریم خصوصی و کنترل دسترسی

## مدل دسترسی

| نقش | Scope | اختیارات اصلی MVP |
|---|---|---|
| `system_admin` | کل سامانه | همه مجموعه‌ها و شعب |
| `organization_admin` | مجموعه | ساختار مشترک و همه شعب مجموعه |
| `school_manager` | شعبه | کاربران و عملیات شعبه |
| `educational_deputy` | شعبه | آموزش، تأیید، رد، قفل و اصلاح رسمی |
| `operator` | شعبه | ورود داده، ثبت‌نام و Import |
| `teacher` | شعبه + کلاس/درس | کلاس‌ها و ارزیابی‌های درس خودش |

`RoleAssignment` اجازه می‌دهد یک کاربر در دو شعبه نقش متفاوت داشته باشد. تخصیص نقش سلسله‌مراتبی است: مدیر شعبه حق ساخت مدیر کل/مجموعه/شعبه دیگر را ندارد.

## کنترل‌های موجود

- JWT کوتاه‌عمر، Refresh چرخشی و blacklist پس از Logout
- غیرفعال‌سازی کاربر بدون حذف تاریخچه
- محدودسازی Query و Object در سطح Branch/Class/Course
- فایل‌های S3 خصوصی با URL امضاشده
- محدودیت Upload: فقط XLSX و حداکثر ۱۰ MiB برای Import؛ تصویر حداکثر ۲ MiB
- جلوگیری از Mass assignment برای statusهای workflow و actorها
- Decimal validation و DB constraints برای نمره
- Audit ورود/خروج، CRUD مهم، تغییر نمره، انتقال، Import و گزارش
- Request ID و JSON log بدون فعال‌سازی PII در Sentry
- Security headerهای Production، HSTS، Secure Cookie و Proxy SSL header
- Rate limit عمومی و Rate limit سخت‌تر برای Login
- حذف منطقی برای داده‌های دامنه

## نکات مهم عملیات

1. `DJANGO_SECRET_KEY`، رمز DB/MinIO و Credentialها نباید Commit شوند.
2. MinIO Console مستقیماً روی اینترنت منتشر نشود؛ Port نمونه برای شبکه مدیریت است.
3. TLS باید در Reverse Proxy/Load Balancer خاتمه یابد.
4. دسترسی Admin فقط برای IP/VPN مدیریتی توصیه می‌شود.
5. بکاپ باید خارج از همان Host نیز کپی و رمزنگاری شود.
6. Log و Snapshot گزارش شامل داده شخصی‌اند؛ Retention و دسترسی آنها باید سیاست سازمانی داشته باشد.
7. `ALLOWED_HOSTS`، CORS و CSRF باید به دامنه‌های واقعی محدود شوند.

## محدودیت امنیتی MVP

2FA، مدیریت دستگاه/نشست پیشرفته، رمزنگاری Field-level، Antivirus فایل، WAF، PITR و Audit کامل Readها در نسخه حرفه‌ای قرار دارند. نبود آنها نباید با امنیت کامل سازمانی اشتباه گرفته شود. قبل از داده واقعی، تست نفوذ و بررسی تنظیمات زیرساخت لازم است.

## Threatهای بررسی‌شده

| تهدید | کنترل |
|---|---|
| مشاهده شعبه دیگر با تغییر UUID | Scope intersection + filtered QuerySet + object check |
| دبیر ویرایش درس دبیر دیگر | offering ownership در Query و command |
| تغییر مستقیم status نمره | status در Serializer read-only و transition service |
| تغییر نمره بعد از قفل | API عادی مسدود؛ correction مجزا + reason + history |
| Import نیمه‌کاره | validate-all سپس transaction-all |
| تکرار همان فایل | SHA-256 + school/type/status duplicate check |
| دستکاری گزارش بعدی | Snapshot و formula version در آرشیو |
