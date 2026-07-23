# نصب Backend هم‌آموز

ساختار فعال پروژه فقط `Backend/hamamooz/apps/*` است و پوشه legacy به نام `Backend/apps` نباید وجود داشته باشد.

## نصب توسعه

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py check
pytest -q
```

برای تولید PDF روی Windows باید DLLهای Pango/GTK در دسترس WeasyPrint باشند. در Docker این کتابخانه‌ها در image نصب می‌شوند.

## قرارداد API

Schema زنده در `/api/v1/schema/` است. برای artifact آفلاین:

```bash
./scripts/generate_openapi.sh
```
