# Backend نسخه MVP سامانه هم‌آموز

این پروژه Backend اجرایی سامانه آموزشی چندشعبه‌ای هم‌آموز است. طراحی فعلی برای ۱۳ شعبه و حدود ۲ تا ۴ هزار دانش‌آموز انجام شده و از سبک **Modular Monolith** استفاده می‌کند: مرز دامنه‌ها مستقل است، اما API، تراکنش‌ها و استقرار در یک سرویس Django باقی می‌مانند.

## قابلیت‌های پیاده‌سازی‌شده

- مجموعه، شعبه، سال تحصیلی، نوبت، پایه و کلاس با ظرفیت
- Custom User، JWT چرخشی، blacklist خروج و نقش متفاوت در شعب مختلف
- جداسازی داده در سطح مجموعه، شعبه، کلاس و درس دبیر
- دانش‌آموز، ولی، ارتباط چندفرزندی، ثبت‌نام تاریخ‌مند، تغییر کلاس و انتقال
- درس پایه، ارائه درس، تخصیص دبیر، ارزیابی و ثبت گروهی نمره
- گردش `draft -> submitted -> approved -> locked` و مسیر رد برای اصلاح
- تاریخچه اصلاح نمره و اصلاح کنترل‌شده نمره قفل‌شده همراه دلیل
- محاسبه نمره نرمال‌شده، معدل درس، معدل نوبت، قبولی و رتبه Dense کلاس
- محاسبه سالانه Decimal با وزن قابل‌تغییر نوبت‌ها، ضریب درس و رتبه مستقل کلاس، پایه و مدرسه
- تاریخچه تغییر وزن‌ها و تنظیم جداگانه نمایش هر رتبه در سطح مدرسه و سال تحصیلی
- دوره مستقل تابستان، ثبت درس و نمره مستقیم آزمون جامع و حد نصاب قبولی nullable
- هفت قالب مستقل RTL کارنامه تحلیلی A3، نهایی A4 و تابستان A4 با تأیید انسانی
- Snapshot تغییرناپذیر و fingerprint، شماره رهگیری و نسخه، PDF رسمی و Word قابل ویرایش
- سیاست محاسبات نسخه‌دار در سطح مجموعه، سال و پایه
- Import اتمیک XLSX برای دانش‌آموز، ثبت‌نام و نمره
- کارنامه A4 فارسی، پیش‌نمایش و آرشیو Snapshot/PDF
- حضور و غیاب روزانه/زنگ، توجیه غیبت، هشدار و اعلان والدین
- داشبورد عملیاتی، Audit، JSON logging، Health Check و Sentry اختیاری
- PostgreSQL، Redis، Celery، FileSystem یا MinIO/S3، Docker Compose و بکاپ دوره‌ای

## شروع سریع با Docker

```bash
cp .env.example .env
# رمزها و DJANGO_SECRET_KEY را در .env تغییر دهید
docker compose up --build -d

docker compose exec web python manage.py seed_demo \
  --admin-password 'A-Strong-Temporary-Password'
```

آدرس‌های پیش‌فرض:

- API: `http://localhost:8000/api/v1/`
- Swagger: `http://localhost:8000/api/v1/docs/`
- ReDoc: `http://localhost:8000/api/v1/redoc/`
- Schema زنده: `http://localhost:8000/api/v1/schema/`
- Admin: `http://localhost:8000/admin/`
- Liveness: `http://localhost:8000/api/v1/health/live/`
- Readiness: `http://localhost:8000/api/v1/health/ready/`

سرویس `release` قبل از `web`، `worker` و `beat`، Migration و `collectstatic` را یک‌بار اجرا می‌کند. در استقرار چند Replica همین الگو باید حفظ شود و Migration داخل هر Replica اجرا نشود.

## اجرای توسعه بدون Docker

Python 3.12، PostgreSQL و Redis مسیر مرجع هستند. SQLite فقط برای توسعه سریع و تست‌هایی که به locking واقعی نیاز ندارند مناسب است.

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

## احراز هویت و Scope درخواست

ورود با username یا email انجام می‌شود:

```http
POST /api/v1/auth/token/
Content-Type: application/json

{"username":"teacher1","password":"..."}
```

در درخواست‌های چندشعبه‌ای:

```http
Authorization: Bearer <access-token>
X-School-ID: <school-uuid>
```

برای منابع مجموعه‌ای می‌توان از `X-Organization-ID` استفاده کرد. در خواندن، نبود هدر، Query را به کل حوزه مجاز کاربر محدود می‌کند. در نوشتن، کاربر غیر از `system_admin` باید Scope صریح بفرستد. UUID نامعتبر، حوزه غیرمجاز، هدرهای متعارض یا تفاوت Scope هدر با شیء مقصد پاسخ 403 می‌گیرند.

## کنترل کیفیت

```bash
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest --cov=hamamooz --cov-report=term-missing
./scripts/generate_openapi.sh ../contracts/openapi.yaml
```

برای بازبینی هدفمند کارنامه‌ها و پورتال خانواده:

```bash
pytest -q \
  tests/test_annual_report_cards.py \
  tests/test_summer_program.py \
  tests/test_report_cards_complete.py \
  tests/test_portal.py
```

تست‌های `select_for_update` و سناریوهای رقابت هم‌زمان باید روی PostgreSQL اجرا شوند. اجرای SQLite برای اثبات رفتار locking معتبر نیست.

## قرارداد OpenAPI

منبع حقیقت قرارداد API، Schema زنده `/api/v1/schema/` و خروجی تولیدشده با دستور زیر است:

```bash
./scripts/generate_openapi.sh ../contracts/openapi.yaml
```

منبع Commit‌شده تیم Frontend فایل `../contracts/openapi.yaml` است. فایل‌های قدیمی `openapi.yaml` و `docs/openapi-schema.yml` داخل پوشه Backend صرفاً Snapshot تاریخی هستند و نباید مبنای Client قرار گیرند.

## نقشه مستندات

- `docs/00-INDEX_FA.md`: نمایه، منبع حقیقت و قواعد نگهداری مستندات
- `docs/01-MVP_SCOPE_FA.md`: دامنه دقیق و وضعیت قابلیت‌ها
- `docs/02-ARCHITECTURE_FA.md`: معماری، مرز ماژول‌ها و جریان‌ها
- `docs/03-DATA_MODEL_FA.md`: مدل داده، قیود، state machine و محاسبات
- `docs/04-API_FA.md`: راهنمای Endpointها، Scope و نمونه درخواست
- `docs/05-SECURITY_FA.md`: RBAC، tenant isolation و کنترل‌های امنیتی
- `docs/06-OPERATIONS_FA.md`: استقرار، Workerها، بکاپ، بازیابی و مانیتورینگ
- `docs/07-TESTING_FA.md`: راهبرد تست و کنترل کیفیت
- `docs/08-DECISIONS_FA.md`: تصمیم‌های معماری و چرایی آن‌ها
- `docs/09-OFFLINE_DEPLOYMENT_FA.md`: استقرار در شبکه محدود
- `docs/10-DELIVERY_MANIFEST_FA.md`: نقشه بسته و کنترل تحویل
- `docs/11-CONFIGURATION_FA.md`: مرجع متغیرهای محیطی
- `docs/12-DEVELOPMENT_FA.md`: راهنمای توسعه و افزودن قابلیت
- `docs/13-RUNBOOK_FA.md`: Runbook خطاها و عملیات نگهداری
- `docs/14-BACKEND_REVIEW_FA.md`: نتیجه بازبینی Backend و ریسک‌های باقی‌مانده
- `docs/API_REFERENCE_FA.md`: مرجع تفصیلی حضور و غیاب
- `docs/import_templates/`: سه قالب ثابت XLSX
