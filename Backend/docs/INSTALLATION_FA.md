# نصب Backend هم‌آموز

ساختار فعال پروژه `Backend/hamamooz/apps/*` است و مسیر legacy به نام `Backend/apps` نباید وجود داشته باشد.

## روش مرجع: Docker

```bash
cp .env.example .env
# Secretها را تغییر دهید
docker compose up --build -d
docker compose ps
curl -fsS http://localhost:8000/api/v1/health/ready/
```

برای MinIO/S3:

```bash
# USE_S3=true و AWS_* کامل
docker compose --profile s3 up --build -d
```

سرویس `release` Migration و collectstatic را پیش از web/worker/beat اجرا می‌کند.

## نصب توسعه محلی

```bash
python3.12 -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env
python manage.py migrate
python manage.py generate_import_templates
python manage.py check
pytest -q
```

برای PDF روی Windows باید DLLهای Pango/GObject در دسترس WeasyPrint باشند. اجرای Docker لینوکسی مسیر یکسان‌تر است.

## داده Demo

```bash
python manage.py seed_demo \
  --admin-password 'A-Strong-Temporary-Password'
```

رمز باید از آرگومان یا `SEED_ADMIN_PASSWORD` بیاید. command idempotent است و ۱۳ شعبه می‌سازد.

## مستندات مرتبط

- تنظیمات: `11-CONFIGURATION_FA.md`
- توسعه: `12-DEVELOPMENT_FA.md`
- استقرار: `06-OPERATIONS_FA.md`
- Runbook: `13-RUNBOOK_FA.md`
- تست: `07-TESTING_FA.md`
