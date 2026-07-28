# راهنمای بسته تحویلی Backend

## نقشه ساختار

```text
Backend/
├── config/                         # settings، URL، ASGI/WSGI و Celery
├── hamamooz/apps/
│   ├── core/                       # Base، Audit، Health و tenancy
│   ├── organizations/              # مجموعه، شعبه، سال، نوبت، پایه و کلاس
│   ├── accounts/                   # کاربر، JWT، RBAC و Scope
│   ├── students/                   # دانش‌آموز، ولی و Enrollment تاریخ‌مند
│   ├── academics/                  # درس، ارزیابی، نمره و محاسبات
│   ├── attendance/                 # حضور، عذر، هشدار و اعلان
│   ├── imports/                    # Import اتمیک XLSX
│   ├── reports/                    # HTML/PDF، Snapshot و آرشیو
│   └── dashboard/                  # شاخص‌های عملیاتی
├── tests/                          # تست Domain/API/Security/Operations
├── templates/reports/              # قالب کارنامه فارسی
├── docs/                           # مستندات و قالب Import
├── scripts/                        # Schema، Backup، Restore و entrypoint
├── nginx/                          # Gateway و نمونه TLS
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

namespace فعال فقط `hamamooz.apps.*` است. مسیر legacy `Backend/apps` نباید ایجاد شود.

## فایل‌های تولیدی و محلی

موارد زیر نباید در بسته سورس جدید اضافه شوند:

```text
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/
db.sqlite3
.coverage
coverage.xml
htmlcov/
media/
staticfiles/
build/
```

`.gitignore` و `.dockerignore` آن‌ها را پوشش می‌دهند. اگر artifact تاریخی از قبل track شده باشد، وجود آن به معنی معتبر بودن برای Commit جاری نیست.

## قرارداد OpenAPI

منبع حقیقت:

```text
/api/v1/schema/
```

Artifact تحویل:

```bash
./scripts/generate_openapi.sh build/openapi.yaml
```

فایل‌های tracked `openapi.yaml` و `docs/openapi-schema.yml` در وضعیت فعلی تاریخی‌اند و بدون regenerate نباید مصرف شوند. در بسته Release، فقط Schema تولیدشده از همان Commit قرار گیرد.

## کنترل بسته

```bash
python -m compileall -q config hamamooz tests
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest --cov=hamamooz --cov-report=term-missing --cov-report=xml
python manage.py spectacular --api-version v1 --file build/openapi.yaml --validate
for file in scripts/*.sh; do sh -n "$file"; done
```

همچنین:

- `docker compose config` با `.env` معتبر اجرا شود.
- Image با user غیر root اجرا شود.
- فایل‌های Import template باز و header آن‌ها کنترل شود.
- PDF فارسی در Image Release تولید شود.
- Migration روی PostgreSQL خالی و upgrade از نسخه قبلی تست شود.
- Backup و Restore روی محیط آزمایشی اجرا شود.

## Manifest Release

هر تحویل باید این اطلاعات را داشته باشد:

```text
Git commit SHA
Image tag و digest
Python/Django/DRF version
Migration head
OpenAPI checksum
Test report و coverage artifact همان Commit
Database compatibility
Required env changes
Backup/rollback instructions
Known limitations
```

## مرز آگاهانه

Frontend در شاخه مستقل است. پنل والد وجود ندارد؛ `in_app` موفق شبیه‌سازی نمی‌شود. SMTP/SMS/S3 واقعی، TLS، off-host backup، scheduler عملیات نگهداری و مانیتورینگ زیرساخت باید در محیط مقصد فراهم شوند.
