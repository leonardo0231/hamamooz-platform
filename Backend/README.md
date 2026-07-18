# Backend نسخه MVP سامانه هم‌آموز

این پروژه یک Backend اجرایی برای مدیریت آموزشی چندشعبه‌ای است. طراحی برای ۱۳ شعبه و حدود ۲ تا ۴ هزار دانش‌آموز انجام شده و ساختار آن Modular Monolith است؛ یعنی مرز دامنه‌ها مستقل است، اما استقرار و تراکنش‌های بین ماژولی در یک سرویس Django باقی می‌ماند.

## قابلیت‌های پیاده‌سازی‌شده

- مجموعه، ۱۳ شعبه، سال تحصیلی، نوبت، پایه و کلاس با ظرفیت
- Custom User، JWT، خروج امن با blacklist و نقش متفاوت در شعب مختلف
- محدودسازی داده در سطح مجموعه، شعبه، کلاس و درس دبیر
- دانش‌آموز، ولی، ارتباط چندفرزندی، ثبت‌نام سالانه، تغییر کلاس و انتقال بین شعب
- درس پایه، ارائه درس، تخصیص و تغییر دبیر
- ارزیابی مستمر، میان‌ترم و پایانی با سقف و وزن قابل تنظیم
- ثبت گروهی نمره، غیبت موجه/غیرموجه و نمره ثبت‌نشده
- گردش `draft -> submitted -> approved -> locked` و مسیر رد برای اصلاح
- تاریخچه همه ثبت/اصلاح‌های نمره و اصلاح کنترل‌شده نمره قفل‌شده با دلیل
- موتور مستقل محاسبه نمره نرمال‌شده، معدل درس، معدل نوبت، قبولی و رتبه Dense کلاس
- سیاست محاسبات نسخه‌دار برای مجموعه/سال/پایه
- Import اتمیک XLSX برای دانش‌آموز، ثبت‌نام و نمره با گزارش ردیف خطادار
- کارنامه A4 فارسی و راست‌چین برای دانش‌آموز یا کل کلاس، پیش‌نمایش و آرشیو Snapshot/PDF
- داشبورد عملیاتی، OpenAPI، Audit، JSON logging، Sentry اختیاری و Health Check
- PostgreSQL، Redis، Celery، MinIO/S3، Docker Compose و بکاپ زمان‌بندی‌شده

## شروع سریع با Docker

```bash
cp .env.example .env
# رمزها و DJANGO_SECRET_KEY را در .env تغییر دهید
docker compose up --build -d
docker compose exec web python manage.py seed_demo \
  --admin-password 'A-Strong-Temporary-Password'
```

آدرس‌ها:

- Swagger: `http://localhost:8000/api/v1/docs/`
- ReDoc: `http://localhost:8000/api/v1/redoc/`
- OpenAPI YAML آماده: `openapi.yaml`
- Admin: `http://localhost:8000/admin/`
- Liveness: `http://localhost:8000/api/v1/health/live/`
- Readiness: `http://localhost:8000/api/v1/health/ready/`

دستور `seed_demo` یک مجموعه، دقیقاً ۱۳ شعبه، سال ۱۴۰۵-۱۴۰۶، دو نوبت، ۱۲ پایه، کلاس‌های نمونه، انواع ارزیابی، سیاست محاسبات و مدیر اولیه می‌سازد. اجرای دوباره آن idempotent است. رمز فقط از آرگومان یا متغیر `SEED_ADMIN_PASSWORD` گرفته می‌شود و داخل کد وجود ندارد.

## اجرای توسعه بدون Docker

Python 3.12، PostgreSQL و Redis پیشنهاد می‌شود. برای تست سریع می‌توان از SQLite و اجرای هم‌زمان Taskها استفاده کرد:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
export DJANGO_SETTINGS_MODULE=config.settings.development
export DATABASE_URL=sqlite:///db.sqlite3
export USE_S3=false
export CELERY_TASK_ALWAYS_EAGER=true
export DJANGO_SECRET_KEY="development-only-secret"
python manage.py migrate
python manage.py generate_import_templates
python manage.py runserver
```

## احراز هویت و انتخاب شعبه

ورود:

```http
POST /api/v1/auth/token/
Content-Type: application/json

{"username":"teacher1","password":"..."}
```

در درخواست‌های چندشعبه‌ای، شعبه فعال با هدر زیر انتخاب می‌شود:

```http
Authorization: Bearer <access-token>
X-School-ID: <school-uuid>
```

در خواندن، نبود هدر Query را به مجموع شعب مجاز کاربر محدود می‌کند. در نوشتن، کاربر غیر از
`system_admin` باید `X-School-ID` یا `X-Organization-ID` صریح بفرستد. UUID نامعتبر، حوزه
غیرمجاز، هدرهای متعارض و تفاوت حوزه هدر با شیء مقصد پاسخ 403 می‌گیرند. محدودسازی فقط در UI
نیست؛ QuerySet، Serializer، Object Permission و Service همگی محدوده را بررسی می‌کنند.

## دستورات کنترل کیفیت

```bash
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --api-version v1 --file openapi.yaml --validate
pytest --cov=hamamooz --cov-report=term-missing
```

اجرای محلی SQLite شامل ۶۴ تست موفق و یک تست ویژه PostgreSQL است؛ پوشش branch-aware برابر
۸۳٫۰۷٪ و Gate برابر ۷۸٪ است. CI علاوه بر آن وابستگی‌ها، Redis/Celery، MinIO خصوصی، Import
دو هزار ردیفی، رقابت هم‌زمان ظرفیت کلاس روی PostgreSQL و بازیابی واقعی بکاپ را کنترل می‌کند.

برای Production از نمونه fail-closed استفاده کنید و تمام placeholderها را جایگزین کنید:

```bash
cp .env.production.example .env
docker compose config
docker compose up --build -d
```

## ساختار مستندات

- `docs/01-MVP_SCOPE_FA.md`: دامنه دقیق و وضعیت پیاده‌سازی
- `docs/02-ARCHITECTURE_FA.md`: معماری، مرز ماژول‌ها و جریان‌ها
- `docs/03-DATA_MODEL_FA.md`: مدل داده، قیود و فرمول محاسبات
- `docs/04-API_FA.md`: راهنمای Endpointها و نمونه درخواست
- `docs/05-SECURITY_FA.md`: RBAC، Tenant isolation و کنترل‌های امنیتی
- `docs/06-OPERATIONS_FA.md`: استقرار، Workerها، بکاپ و بازیابی
- `docs/07-TESTING_FA.md`: راهبرد و نتیجه تست
- `docs/08-DECISIONS_FA.md`: تصمیم‌های معماری و چرایی آنها
- `docs/09-OFFLINE_DEPLOYMENT_FA.md`: انتقال به سرور فاقد دسترسی GitHub/سایت‌های خارجی
- `docs/10-DELIVERY_MANIFEST_FA.md`: نقشه بسته، کنترل‌های نهایی و مرز آگاهانه MVP
- `docs/import_templates/`: سه قالب ثابت XLSX قابل استفاده
