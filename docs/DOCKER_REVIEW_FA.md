# گزارش بررسی و اصلاح Docker هم‌آموز

## هدف

اجرای کامل سامانه با یک Compose از ریشه پروژه، شامل PostgreSQL، Backend،
Frontend و سرویس‌های لازم برای Import و Report.

## ایرادهای نسخه ورودی

1. Compose ریشه‌ای به فایل `.env` وابسته بود و بدون آن به‌دلیل
   `POSTGRES_PASSWORD:?` اجرا نمی‌شد.
2. فایل `.env` واقعی همراه ZIP قرار گرفته بود و پورت API آن `8001` بود، در
   حالی که README و مقدار پیش‌فرض Compose پورت `8000` را اعلام می‌کردند.
3. حساب توسعه به‌صورت خودکار ساخته نمی‌شد؛ در نتیجه Stack بالا می‌آمد اما
   ورود اولیه نیازمند اجرای دستی `seed_demo` بود.
4. Nginx فرانت `client_max_body_size` نداشت؛ فایل‌های Import بزرگ‌تر از حد
   پیش‌فرض Nginx می‌توانستند با خطای 413 متوقف شوند.
5. `static_data` و `media_data` به Frontend متصل نبودند؛ Gunicorn نیز برای سرو
   مستقیم این فایل‌ها طراحی نشده است.
6. Proxy از `Host $proxy_host` استفاده می‌کرد و پاسخ‌های دارای URL مطلق
   می‌توانستند hostname داخلی `web:8000` را به Browser برگردانند.
7. ترتیب Startup برای Migration مناسب بود، اما Bootstrap داده و حساب مدیر در
   زنجیره Dependency وجود نداشت.

## اصلاحات اعمال‌شده

- Compose ریشه به Stack محلی all-in-one تبدیل شد و بدون `.env` نیز کار می‌کند.
- Defaults محلی قابل Override در `.env.example` قرار گرفتند.
- سرویس `bootstrap` پس از Migration اجرا می‌شود و `seed_demo` را به‌شکل
  idempotent اجرا می‌کند.
- `web` تا موفقیت Bootstrap و `frontend` تا Healthy شدن `web` منتظر می‌مانند.
- Healthcheckها دارای `start_period` و Retry مناسب‌تر شدند.
- Worker و Beat در Stack پیش‌فرض حفظ شدند تا Import و Report واقعاً پردازش شوند.
- Nginx فرانت API و Admin را به Backend Proxy می‌کند و static/media را از
  Volume مشترک سرو می‌کند.
- محدودیت Upload روی ۳۰ مگابایت و Timeout پردازش روی ۱۸۰ ثانیه تنظیم شد.
- Host عمومی درخواست حفظ می‌شود تا URL داخلی Docker وارد UI نشود.
- فایل‌های `.env` واقعی از بسته خروجی حذف شدند و فقط Template باقی ماند.
- Smoke script برای Bash و PowerShell اضافه شد.

## فرمان اجرا

```bash
docker compose up --build -d
```

یا اجرای همراه Smoke test:

```bash
./scripts/docker-smoke.sh
```

PowerShell:

```powershell
.\scripts\docker-smoke.ps1
```

## اعتبارسنجی انجام‌شده

- Parse و بررسی ساختار Compose: موفق
- بررسی Dependency chain سرویس‌ها: موفق
- تست Syntax تنظیمات Nginx با `nginx -t`: موفق
- TypeScript typecheck: موفق
- Static lint فرانت‌اند: موفق
- Production frontend build: موفق
- تست‌های فرانت‌اند: ۲۱ از ۲۱ موفق
- بررسی Syntax فایل‌های Python با `compileall`: موفق

Docker Engine در محیط بررسی نصب نبود؛ بنابراین Pull/Build واقعی Imageهای
Docker و اجرای Containerها در همین محیط امکان‌پذیر نبود. Smoke script داخل
خروجی این مرحله را روی سیستم دارای Docker به‌صورت خودکار انجام می‌دهد.
