# راهنمای توسعه Backend

## آماده‌سازی

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env
python manage.py migrate
python manage.py generate_import_templates
```

برای توسعه سریع می‌توان SQLite و task eager استفاده کرد، اما قبل از Merge تست PostgreSQL الزامی است.

## ساختار هر ماژول

```text
models.py        ساختار داده و constraint
serializers.py   validation ورودی/خروجی و جلوگیری از mass assignment
views.py         HTTP، Query scope و action mapping
services.py      command دامنه، transaction و row lock
tasks.py         orchestration غیرهم‌زمان و retry
permissions.py   قواعد خاص دامنه در صورت نیاز
selectors.py     Queryهای خواندنی پیچیده در صورت نیاز
migrations/      تغییر schema/data
tests/           سناریوهای رفتار و regression
```

منطق دامنه سنگین نباید داخل View یا Celery task تکرار شود. Task شناسه می‌گیرد، Service را صدا می‌زند و نتیجه serializable برمی‌گرداند.

## افزودن Model

1. Tenant ownership را صریح تعیین کنید.
2. `on_delete` را بر اساس نیاز تاریخچه انتخاب کنید؛ داده رسمی معمولاً `PROTECT` است.
3. unique/check constraint را در DB اضافه کنید.
4. index Queryهای پرتکرار را مستند کنید.
5. رفتار soft delete و restore را بررسی کنید.
6. Migration و rollback compatibility را ارزیابی کنید.
7. مدل را در `03-DATA_MODEL_FA.md` اضافه کنید.

## افزودن Endpoint

1. QuerySet با Scope مجاز شروع شود، نه اینکه بعداً filter شود.
2. برای هر action ناامن `required_roles_by_action` صریح تعریف شود؛ نبود mapping باید deny بماند.
3. Serializer Tenant relationها و immutable fieldها را validate کند.
4. mutation و Audit داخل transaction باشند.
5. action جدید در OpenAPI، `04-API_FA.md` و تست API ثبت شود.
6. برای عملیات طولانی Job/Task با وضعیت و idempotency استفاده شود.

نمونه skeleton:

```python
class ExampleViewSet(AuditedModelViewSet):
    queryset = Example.objects.none()
    serializer_class = ExampleSerializer
    required_roles_by_action = {
        "create": [Role.SYSTEM_ADMIN, Role.ORGANIZATION_ADMIN],
    }

    def get_queryset(self):
        return Example.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        )
```

## تراکنش و Task

- validation ارزان قبل از lock انجام شود.
- ردیف‌های رقابتی با ترتیب ثابت lock شوند تا deadlock کم شود.
- Task فقط با `transaction.on_commit` صف شود.
- retry فقط برای خطاهای موقت باشد.
- Job باید claim/idempotency و timeout recovery داشته باشد.
- ارسال خارجی داخل transaction DB انجام نشود.

## Query و Performance

- Listها صفحه‌بندی باقی بمانند.
- `select_related` برای FK و `prefetch_related` برای مجموعه‌ها استفاده شود.
- از Query داخل loop جلوگیری شود.
- aggregation گزارش با Query گروهی انجام شود.
- index جدید با Query plan PostgreSQL و داده نزدیک Production بررسی شود.

## تست لازم برای قابلیت جدید

حداقل:

- happy path Service
- validation و constraint
- role مجاز و غیرمجاز
- cross-tenant access
- API request/response
- rollback در خطای میانی
- idempotency یا concurrency در صورت mutation حساس
- migration test در تغییر داده
- OpenAPI generation

## سبک کد

```bash
ruff check .
ruff format .
```

- Python 3.12 syntax هدف است.
- line length برابر ۱۰۰ است.
- importهای first-party: `config`, `hamamooz`.
- Migrationها از Ruff مستثنا هستند.
- comment باید چرایی تصمیم غیرواضح را توضیح دهد، نه تکرار کد.

## دستورات کاربردی

```bash
make dev
make test
make lint
make format
make migrate
make seed
make templates
make schema
```

`make check` از `check --deploy` استفاده می‌کند؛ برای نتیجه Production، Settings و Environment production معتبر لازم است.

## Definition of Done

```text
[ ] invariant دامنه و Scope مشخص است
[ ] migration و constraint اضافه شده است
[ ] action role mapping صریح دارد
[ ] audit و redaction بررسی شده است
[ ] تست PostgreSQL و regression نوشته شده است
[ ] OpenAPI تولید و validate شده است
[ ] مستندات شماره‌دار به‌روزرسانی شده‌اند
[ ] env/operation change مستند شده است
[ ] rollback و failure mode مشخص است
```
