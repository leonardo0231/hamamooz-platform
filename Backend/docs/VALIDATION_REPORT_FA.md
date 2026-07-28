# گزارش اعتبارسنجی بسته اصلاح‌شده

> **وضعیت:** این گزارش تاریخی و مربوط به محیط ساخت بسته است؛ برای وضعیت جاری به `14-BACKEND_REVIEW_FA.md` و خروجی CI همان Commit مراجعه کنید.

## کنترل‌های اجراشده در محیط ساخت ZIP

- `python -m compileall` روی کل Backend: موفق.
- parse فایل `pyproject.toml` با parser استاندارد Python: موفق.
- parse فایل `docker-compose.yml`: موفق.
- syntax check تمام اسکریپت‌های POSIX shell پس از یکسان‌سازی LF: موفق.
- بررسی AST برای نام‌های تعریف‌نشده و importهای بلااستفاده: بدون خطای قطعی؛ re-exportهای شناخته‌شده
  و importهای داخل تابع جداگانه بررسی شدند.
- بررسی حذف artifactهای محلی مانند `.venv`، cache، SQLite و coverage از ZIP: موفق.

## کنترل‌هایی که در محیط ساخت قابل اجرا نبودند

محیط ساخت دسترسی قابل اتکا به registry بسته‌ها نداشت، بنابراین dependencyهای پروژه نصب نشدند و
ادعای اجرای Django/Ruff/Pytest یا تولید PDF در این محیط نمی‌شود. این کنترل‌ها باید در checkout مقصد
یا image پروژه اجرا شوند:

```bash
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest -q
python manage.py spectacular --api-version v1 --file build/openapi.yaml --validate
```

تست PDF روی Windows به Pango/GObject نیاز دارد. اجرای Docker راه پیشنهادی برای حذف تفاوت native
Windows است. تست‌های locking و concurrency باید روی PostgreSQL اجرا شوند، نه SQLite.
