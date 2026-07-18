# راهنمای بسته تحویلی MVP

## مبنای تحلیل

دامنه و معیارهای پذیرش از دو ورودی `Pasted text(184).txt` و `School Platform(1)(2).pdf` استخراج و با هم تطبیق داده شد. در تعارض احتمالی، نیازهای صریح MVP و سادگی عملیاتی برای ۱۳ شعبه و ۲ تا ۴ هزار دانش‌آموز اولویت داشته است.

## نقشه ساختار

```text
hamamooz-platform/
├── .github/workflows/backend-ci.yml   # CI بک‌اند
├── README.md                          # نقطه شروع مخزن
└── Backend/
    ├── config/                        # تنظیمات dev/test/prod، URL، ASGI/WSGI و Celery
    ├── hamamooz/apps/
    │   ├── core/                      # مدل‌های پایه، Audit، Log، Health و Tenant helpers
    │   ├── organizations/             # مجموعه، شعبه، سال، نوبت، پایه و کلاس
    │   ├── accounts/                  # Custom User، JWT، RBAC و Scope دسترسی
    │   ├── students/                  # دانش‌آموز، ولی، ثبت‌نام و انتقال
    │   ├── academics/                 # درس، ارائه، ارزیابی، نمره و موتور محاسبه
    │   ├── imports/                   # Import اتمیک XLSX و Queue
    │   ├── reports/                   # Snapshot، HTML/PDF و آرشیو رسمی
    │   └── dashboard/                 # شاخص‌های عملیاتی
    ├── tests/                         # تست‌های Domain/API/PDF/Security/Operations
    ├── templates/reports/             # قالب فارسی A4
    ├── docs/                          # مستندات فارسی و قالب‌های واقعی XLSX
    ├── scripts/                       # Entry point، Backup و Restore
    ├── openapi.yaml                   # قرارداد API نسخه ۱
    ├── docker-compose.yml             # Web/Worker/Postgres/Redis/MinIO/Backup
    ├── Dockerfile
    └── pyproject.toml
```

## کنترل‌های انجام‌شده روی نسخه تحویلی

| کنترل | نتیجه |
|---|---|
| Ruff | بدون خطا |
| Django system check | بدون خطا |
| Migration drift | تغییری شناسایی نشد |
| OpenAPI validation | بدون هشدار یا خطا |
| Pytest | ۶۴ تست محلی موفق + یک تست concurrency ویژه PostgreSQL CI |
| Coverage | ۸۳٫۰۷٪ branch-aware؛ Gate برابر ۷۸٪ |
| Dependency audit | بدون آسیب‌پذیری شناخته‌شده |
| Backup/restore | Dump، checksum و Restore ایزوله در CI |
| PDF | تولید واقعی، یک صفحه A4، RTL و بازبینی تصویری |
| Shell scripts | عبور از `bash -n` |
| Docker Compose | YAML و ارتباط سرویس‌ها بررسی شد |

## شروع پیشنهادی

برای اجرای محلی از `Backend/README.md` شروع کنید. پیش از Production، Checklist فایل `06-OPERATIONS_FA.md` و راهنمای انتقال آفلاین `09-OFFLINE_DEPLOYMENT_FA.md` باید کامل شوند. فایل `.env.example` صرفاً نمونه است و هیچ رمز نمونه‌ای نباید در Production باقی بماند.

## مرز آگاهانه MVP

رابط کاربری، هوش مصنوعی/ML، تحلیل پیشرفته، حضور و غیاب کامل، رفتار، مشاوره و پنل مستقل اولیا/دانش‌آموز عمداً وارد این بسته نشده‌اند. مدل داده، Audit و مرز ماژول‌ها امکان افزودن قابلیت‌های بعدی را فراهم می‌کند، اما بسته حاضر ادعای قابلیت پیاده‌سازی‌نشده ندارد.
