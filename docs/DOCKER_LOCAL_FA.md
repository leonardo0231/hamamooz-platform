# اجرای یکپارچه هم‌آموز با Docker

این راهنما برای اجرای محلی کل سامانه از ریشه پروژه است. فایل Compose داخل
`Backend/` برای استقرار مستقل Backend و فایل Compose داخل `Frontend/` برای
اجرای مستقل Frontend هستند؛ برای اجرای هم‌زمان همه اجزا فقط از فایل ریشه
استفاده کنید.

## اجرای اولیه

```bash
docker compose up --build -d
```

این دستور سرویس‌های زیر را اجرا می‌کند:

- `db`: PostgreSQL
- `redis-cache`: کش Django
- `redis-broker`: Broker و Result Backend سلری
- `release`: اجرای Migration و `collectstatic`
- `bootstrap`: ساخت داده نمایشی و مدیر محلی
- `web`: Django + Gunicorn
- `worker`: پردازش Import، Report، Calculation و Notification
- `beat`: زمان‌بندی کارهای دوره‌ای
- `frontend`: Nginx و فایل‌های Buildشده فرانت‌اند

`web` فقط پس از موفقیت Migration و Bootstrap اجرا می‌شود و `frontend` نیز تا
Healthy شدن Backend منتظر می‌ماند.

## آدرس‌ها

- رابط کاربری: `http://localhost:5173`
- API از مسیر یکپارچه: `http://localhost:5173/api/v1/`
- API مستقیم: `http://localhost:8000/api/v1/`
- Swagger: `http://localhost:5173/api/v1/docs/`
- Django Admin: `http://localhost:5173/admin/`

## حساب توسعه محلی

- نام کاربری: `admin`
- رمز عبور: `Admin123!ChangeMe`

این مقادیر فقط برای محیط محلی هستند. برای تغییر آن‌ها یک `.env` از روی
`.env.example` بسازید و مقادیر `SEED_ADMIN_USERNAME` و
`SEED_ADMIN_PASSWORD` را تغییر دهید.

نکته: اگر کاربر قبلاً در Volume دیتابیس ایجاد شده باشد، تغییر مقدار رمز در
`.env` رمز حساب موجود را عوض نمی‌کند. برای تغییر رمز:

```bash
docker compose exec web python manage.py changepassword admin
```

## بررسی وضعیت

```bash
docker compose ps
docker compose logs --tail=100 release bootstrap web frontend db
docker compose exec web python manage.py check
```

Healthcheck اصلی:

```bash
curl http://localhost:5173/api/v1/health/ready/
```

## Smoke یکپارچه و ایزوله

برای بررسی clean boot بدون استفاده از `.env`، volume یا پورت‌های اجرای محلی، از
smoke زیر استفاده کنید:

```bash
bash scripts/docker-integration-smoke.sh
```

این فرمان imageها را می‌سازد و سپس health، login، dashboard، students، import
فایل جامع XLSX و preview گزارش را از مسیر HTTP عمومی می‌سنجد. در پایان فقط
containerها و volumeهای project موقت خود را پاک می‌کند.

در WSL که `docker` به Docker Desktop متصل نیست اما Docker Desktop ویندوز در
دسترس است:

```bash
DOCKER_BIN=docker.exe bash scripts/docker-integration-smoke.sh
```

برای نگه‌داشتن منابع فقط جهت debug می‌توان `KEEP_SMOKE_CONTAINERS=true` تنظیم
کرد؛ در حالت عادی cleanup اجباری است.

## بازسازی یا پاک‌سازی

```bash
# بازسازی Imageها و اجرای مجدد
docker compose up --build -d

# توقف بدون حذف داده
docker compose down

# حذف کامل داده محلی
docker compose down --volumes
```

پس از حذف Volumeها، Bootstrap در اجرای بعدی دوباره حساب مدیر و داده نمایشی را
می‌سازد.

## نکات طراحی Stack

- Frontend در زمان Build از `/api/v1/` استفاده می‌کند؛ بنابراین Browser به
  hostname داخلی Docker وابسته نیست.
- Nginx فرانت درخواست‌های API و Admin را به `web:8000` Proxy می‌کند.
- فایل‌های `/static/` و `/media/` از Volume مشترک مستقیم توسط Nginx ارائه
  می‌شوند؛ Gunicorn مسئول سرو فایل نیست.
- `client_max_body_size` روی ۳۰ مگابایت قرار دارد تا Importهای Excel و فایل‌های
  شواهد با خطای `413 Request Entity Too Large` متوقف نشوند.
- PostgreSQL به Host Publish نشده و فقط در شبکه داخلی Compose در دسترس است.
