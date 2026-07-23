# راهنمای بسته تحویلی Backend

## نقشه ساختار

```text
Backend/
├── config/                         # settings، URL، ASGI/WSGI و Celery
├── hamamooz/apps/
│   ├── core/                       # مدل پایه، Audit، Health و tenancy
│   ├── organizations/              # مجموعه، شعبه، سال، نوبت، پایه و کلاس
│   ├── accounts/                   # کاربر، JWT، RBAC و scope
│   ├── students/                   # دانش‌آموز، ولی و ثبت‌نام تاریخ‌مند
│   ├── academics/                  # درس، ارزیابی، نمره و محاسبات
│   ├── attendance/                 # حضور و غیاب، عذر، هشدار و اعلان
│   ├── imports/                    # Import اتمیک و محدودشده XLSX
│   ├── reports/                    # HTML/PDF، snapshot و آرشیو
│   └── dashboard/                  # شاخص‌های نوبت انتخاب‌شده
├── tests/                          # تست‌های Domain/API/Security/Operations
├── templates/reports/              # قالب کارنامه فارسی
├── docs/                           # مستندات و قالب‌های Import
├── scripts/                        # schema، backup، restore و entrypoint
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

پوشه قدیمی `Backend/apps` بخشی از معماری فعال نیست و نباید دوباره ایجاد شود. importهای معتبر با
namespace `hamamooz.apps.*` هستند.

## قرارداد OpenAPI

Schema استاتیک داخل repository نگهداری نمی‌شود تا stale نشود. منبع حقیقت endpoint زیر است:

```text
/api/v1/schema/
```

برای artifact قابل تحویل:

```bash
./scripts/generate_openapi.sh build/openapi.yaml
```

## کنترل‌های بسته

در محیط ساخت این ZIP، کنترل‌های مستقل از dependency اجرا شده‌اند: compile تمام Pythonها، parse
`pyproject.toml`، parse Compose، syntax اسکریپت‌های shell، بررسی AST و پاک‌سازی artifactهای محلی.
کنترل‌های Django/Ruff/Pytest/OpenAPI باید پس از نصب dependencyها در checkout مقصد اجرا شوند؛
دستورهای دقیق در `docs/07-TESTING_FA.md` و `COMMIT_INSTRUCTIONS_FA.md` آمده است.

## مرز آگاهانه

پنل مستقل والد در این نسخه وجود ندارد؛ بنابراین channel داخلی والد به‌صورت `skipped` ثبت می‌شود و
ارسال واقعی باید از email یا SMS پیکربندی‌شده انجام شود. رابط کاربری در branch مستقل frontend است.
