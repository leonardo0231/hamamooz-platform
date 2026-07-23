# راهبرد تست و کنترل کیفیت

## اصل اعتبارسنجی

نتیجه معتبر باید از همان Commit، dependency lock، Settings و دیتابیس مقصد ثبت شود. عدد ثابت coverage یا تعداد تست، جای CI artifact همان Commit را نمی‌گیرد.

در بازبینی استاتیک این شاخه ۸۴ تابع تست شناسایی شد، اما این عدد به معنی اجرای موفق آن‌ها نیست. فایل tracked `coverage.xml` نیز artifact تاریخی است و نباید بدون rerun مبنای پذیرش قرار گیرد.

## هرم تست

| لایه | هدف | نمونه |
|---|---|---|
| Model/validator | constraint و validation محلی | کد ملی، تاریخ، حجم فایل |
| Service | invariant و transaction | انتقال، bulk score، finalize |
| API | auth، Scope، serializer و response | workflowهای کامل |
| Security regression | جلوگیری از نشت و escalation | cross-school, role management |
| Integration | PostgreSQL، Redis، storage و PDF | locking، task، WeasyPrint |
| Operational | command و backup/restore | seed، template، retention |

## حوزه‌های پوشش موجود

- JWT، login با username/email، blacklist و revoke
- RoleAssignment، Scope header و جداسازی شعبه
- Enrollment تاریخ‌مند، ظرفیت و رقابت هم‌زمان
- workflow ارزیابی، locked correction، policy و رتبه
- Attendance roster، finalize، excuse، alert و notification
- Import معتبر/خراب، rollback، duplicate و محدودیت حجم
- Report preview/PDF/snapshot، confinement و idempotency
- Dashboard، health، forwarded IP و management commandها

## اجرای مرجع

```bash
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest -q
pytest --cov=hamamooz --cov-report=term-missing --cov-report=xml
python manage.py spectacular --api-version v1 --file build/openapi.yaml --validate
```

Threshold فعلی line coverage در `pyproject.toml` برابر ۷۸٪ است. Branch coverage اندازه‌گیری می‌شود، اما fail threshold مستقل ندارد؛ پیشنهاد می‌شود برای branch coverage نیز threshold تدریجی تعریف شود.

## اجرای Docker

```bash
docker compose build
docker compose run --rm release
docker compose run --rm web pytest -q
docker compose run --rm web python manage.py spectacular \
  --api-version v1 --file build/openapi.yaml --validate
```

در CI بهتر است سرویس‌های DB و Redis بالا بیایند، سپس test container با Settings test و PostgreSQL اجرا شود.

## تست‌های اجباری روی PostgreSQL

SQLite مرجع معتبر برای `select_for_update` و race condition نیست. موارد زیر باید روی PostgreSQL اجرا شوند:

- رقابت دو Enrollment برای آخرین ظرفیت کلاس
- duplicate/claim هم‌زمان Import و Report
- Attendance finalize/correction هم‌زمان
- alert evaluation و notification claim
- constraintهای partial/conditional unique
- migrationهای داده و schema

## WeasyPrint

روی Windows به Pango/GObject نیاز است:

```bat
set WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin
python -c "from weasyprint import HTML; print('WeasyPrint OK')"
```

Image لینوکسی پروژه مسیر مرجع برای حذف تفاوت native است.

## Contract و Documentation test

- Schema باید از همان Commit تولید شود.
- Routeهای `config/api_urls.py` و actionهای ViewSet باید در Schema حاضر باشند.
- فایل‌های static قدیمی نباید مبنای Client generation باشند.
- نمونه Payloadهای `04-API_FA.md` باید حداقل با Schema validate شوند.
- فهرست envهای `11-CONFIGURATION_FA.md` باید با Settings و Compose مقایسه شود.

## کنترل انجام‌شده در این بازبینی

موارد مستقل از dependency با موفقیت اجرا شدند:

```text
python -m compileall روی config/hamamooz/tests
parse pyproject.toml
parse docker-compose.yml
sh -n برای scripts/*.sh
```

اجرای Django/Pytest در محیط بازبینی به دلیل نصب نبودن dependencyهای پروژه ممکن نبود؛ بنابراین ادعای pass شدن suite در این سند ثبت نمی‌شود.
