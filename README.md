# هم‌آموز (HamAmoz) - MVP Backend

این مخزن فقط Backend نسخه MVP سامانه چندشعبه‌ای مدارس را در بر می‌گیرد و تمام کد اجرایی آن در `Backend/` قرار دارد.

شروع سریع:

```bash
cd Backend
cp .env.example .env
docker compose up --build
```

پس از آماده‌شدن سرویس‌ها:

- API: `http://localhost:8000/api/v1/`
- Swagger: `http://localhost:8000/api/v1/docs/`
- ReDoc: `http://localhost:8000/api/v1/redoc/`
- Django Admin: `http://localhost:8000/admin/`

جزئیات نصب، معماری، مدل داده، دسترسی‌ها و عملیات در [Backend/README.md](Backend/README.md) و پوشه [Backend/docs](Backend/docs) آمده است.
