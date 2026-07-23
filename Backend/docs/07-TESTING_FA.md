# راهبرد تست و کنترل کیفیت

## اصل اعتبارسنجی

نتیجه تست باید از همان checkout، dependency lock و دیتابیس مقصد ثبت شود. این سند عدد ثابت یا
ادعای قدیمی درباره تعداد تست و درصد coverage نگه نمی‌دارد؛ خروجی CI و اجرای محلی منبع حقیقت است.

## حوزه‌های پوشش

| حوزه | فایل‌ها و سناریوهای اصلی |
|---|---|
| احراز هویت و دسترسی | JWT، login با username/email، blacklist، نقش و جداسازی شعبه |
| دانش‌آموز و ثبت‌نام | ظرفیت، تاریخ مؤثر، تغییر کلاس تاریخ‌مند، انتقال و جلوگیری از بازنویسی تاریخچه |
| آموزش و نمره | گردش ارزیابی، ثبت گروهی، قفل، اصلاح، سیاست محاسبه، کامل‌بودن نتیجه و رتبه |
| حضور و غیاب | roster تاریخ‌مند، ثبت گروهی، finalize، اصلاح، عذر، cancel، alert و notification |
| Import | XLSX معتبر/خراب، rollback، محدودیت row/column و حفاظت در برابر decompression bomb |
| گزارش | preview HTML، PDF، snapshot، confinement فایل رسانه و idempotency task |
| عملیات | health/readiness، management commandها، Celery و backup/restore |

## اجرای محلی

```bash
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest -q
python manage.py spectacular --api-version v1 --file build/openapi.yaml --validate
```

برای coverage:

```bash
pytest --cov=hamamooz --cov-report=term-missing --cov-report=xml
```

## Windows و WeasyPrint

تست‌های PDF به Pango/GObject نیاز دارند. روی Windows باید MSYS2/Pango نصب و مسیر DLL تنظیم شود:

```bat
set WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin
python -c "from weasyprint import HTML; print('WeasyPrint OK')"
```

راه مرجع و یکسان‌تر، اجرای suite داخل image لینوکسی پروژه است:

```bash
docker compose build
docker compose run --rm release
docker compose run --rm web pytest -q
```

## تست‌هایی که باید روی PostgreSQL اجرا شوند

SQLite مرجع معتبری برای `select_for_update` و رقابت هم‌زمان نیست. سناریوهای ظرفیت ثبت‌نام، claim
اعلان، ارزیابی هشدار، تولید گزارش و Import هم‌زمان باید در CI با PostgreSQL اجرا شوند.
