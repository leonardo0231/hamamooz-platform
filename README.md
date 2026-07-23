# HamAmoz Platform

سامانه تحت وب مدیریت آموزشی چندشعبه‌ای هم‌آموز.

این Repository به‌صورت Monorepo نگهداری می‌شود و شامل Backend، Frontend، قرارداد API و مستندات یکپارچه‌سازی است.

## ساختار پروژه

```text
hamamooz-platform/
├── Backend/       # Django REST Framework Backend
├── Frontend/      # Web Frontend
├── contracts/     # OpenAPI contract and API changelog
├── docs/          # Shared integration documentation
└── .github/       # GitHub workflows and review rules
```

پوشه `Frontend/` پس از ادغام شاخه بک‌اند در `main`، روی شاخه `frontend/mvp-bootstrap` ایجاد می‌شود.

## Branchها

این Repository فقط سه Branch دائمی دارد:

- `main`: نسخه یکپارچه و قابل انتشار
- `backend/mvp-bootstrap`: توسعه Backend
- `frontend/mvp-bootstrap`: توسعه Frontend

توسعه‌دهندگان Backend فقط در `Backend/`، `contracts/` و مستندات API تغییر ایجاد می‌کنند.

توسعه‌دهندگان Frontend فقط در `Frontend/` تغییر ایجاد می‌کنند.

هیچ تغییر مستقیمی نباید روی `main` Push شود. ورود تغییرات به `main` فقط از طریق Pull Request انجام می‌شود.

## اجرای Backend

```bash
cd Backend
cp .env.example .env
docker compose up --build
```

سرویس‌ها پس از اجرا:

- API: `http://localhost:8000/api/v1/`
- Swagger: `http://localhost:8000/api/v1/docs/`
- ReDoc: `http://localhost:8000/api/v1/redoc/`
- OpenAPI Schema: `http://localhost:8000/api/v1/schema/`
- Admin: `http://localhost:8000/admin/`

## قرارداد API

منبع اصلی قرارداد API فایل زیر است:

```text
contracts/openapi.yaml
```

این فایل باید مستقیماً از کد Backend تولید شود و نباید به‌صورت دستی ویرایش شود.

```bash
cd Backend
./scripts/generate_openapi.sh ../contracts/openapi.yaml
```

هر تغییری در Endpoint، Request، Response، Permission، Status Code، Header یا Enum باید همراه با تولید مجدد قرارداد OpenAPI باشد.

## راهنمای Frontend

راهنمای اتصال Frontend به Backend در فایل زیر قرار دارد:

```text
docs/FRONTEND_HANDOFF_FA.md
```

ماتریس وضعیت یکپارچه‌سازی و قالب تحویل تغییر API:

```text
docs/INTEGRATION_MATRIX.md
docs/API_CHANGE_TEMPLATE.md
```

## مستندات Backend

مستندات کامل Backend در مسیر زیر قرار دارند:

```text
Backend/docs/
```
