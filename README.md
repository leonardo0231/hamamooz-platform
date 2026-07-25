# HamAmoz Platform

سامانه‌ی تحت وب مدیریت آموزشی چندشعبه‌ای **هم‌آموز**.

این Repository به‌صورت Monorepo طراحی شده و محل یکپارچه‌سازی Backend، Frontend، قرارداد رسمی API و مستندات مشترک محصول است.

## وضعیت Repository

| Branch | مسئولیت | وضعیت مورد انتظار |
|---|---|---|
| `main` | نسخه‌ی یکپارچه، قابل بررسی و آماده‌ی انتشار | فقط از طریق Pull Request به‌روزرسانی می‌شود |
| `backend/mvp-bootstrap` | توسعه‌ی Django REST API و قرارداد OpenAPI | منبع فعلی پیاده‌سازی Backend |
| `frontend/mvp-bootstrap` | توسعه‌ی رابط کاربری و API Client | مصرف‌کننده‌ی قرارداد رسمی API |

هیچ تغییر مستقیمی نباید روی `main` Push شود. تغییرات هر تیم ابتدا روی Branch تخصصی خود توسعه و تست می‌شوند و سپس با Pull Request وارد `main` می‌شوند.

## ساختار هدف پروژه

```text
hamamooz-platform/
├── Backend/       # Django REST Framework Backend
├── Frontend/      # Web Frontend
├── contracts/     # OpenAPI contract and API changelog
├── docs/          # Shared integration documentation
└── .github/       # CI workflows, templates and review rules
```

ممکن است بعضی مسیرها تا زمان ادغام Branch مربوطه هنوز در `main` وجود نداشته باشند.

## شروع سریع Backend

پیاده‌سازی Backend در Branch زیر نگهداری می‌شود:

```bash
git switch backend/mvp-bootstrap
cd Backend
cp .env.example .env
docker compose up --build
```

آدرس‌های پیش‌فرض توسعه:

- API: `http://localhost:8000/api/v1/`
- Swagger: `http://localhost:8000/api/v1/docs/`
- ReDoc: `http://localhost:8000/api/v1/redoc/`
- OpenAPI Schema: `http://localhost:8000/api/v1/schema/`
- Django Admin: `http://localhost:8000/admin/`

مستندات کامل Backend در `Backend/README.md` و `Backend/docs/` قرار می‌گیرند.

## قرارداد رسمی API

Frontend نباید Endpoint، Payload، Response، Enum، Permission یا Status Code را از روی حدس پیاده‌سازی کند.

منبع رسمی قرارداد ماشین‌خوان API:

```text
contracts/openapi.yaml
```

تا پیش از ادغام Backend در `main`، نسخه‌ی جاری قرارداد در Branch زیر قابل مشاهده است:

- [`contracts/openapi.yaml` در backend/mvp-bootstrap](https://github.com/leonardo0231/hamamooz-platform/blob/backend/mvp-bootstrap/contracts/openapi.yaml)
- [`contracts/API_CHANGELOG.md` در backend/mvp-bootstrap](https://github.com/leonardo0231/hamamooz-platform/blob/backend/mvp-bootstrap/contracts/API_CHANGELOG.md)
- [`contracts/README.md` در backend/mvp-bootstrap](https://github.com/leonardo0231/hamamooz-platform/blob/backend/mvp-bootstrap/contracts/README.md)

فایل OpenAPI مستقیماً از کد Backend تولید می‌شود و نباید دستی ویرایش شود:

```bash
cd Backend
./scripts/generate_openapi.sh ../contracts/openapi.yaml
```

هر تغییر در موارد زیر باید همراه با تولید مجدد قرارداد و ثبت در Changelog باشد:

- Endpoint یا HTTP Method
- Request/Response Schema
- Query، Path یا Header Parameter
- Authentication و Permission
- Status Code و Error Code
- Pagination، Enum و Nullability

## راهنمای Frontend

راهنمای اجرایی اتصال Frontend به Backend در فایل زیر قرار دارد:

- [`docs/FRONTEND_HANDOFF_FA.md`](docs/FRONTEND_HANDOFF_FA.md)

Frontend پیش از شروع هر Feature باید:

1. وضعیت Endpoint را بررسی کند.
2. Typeها و API Client را از OpenAPI تولید یا با آن اعتبارسنجی کند.
3. Base URL، Token و Scope Headerها را در یک API Client مرکزی مدیریت کند.
4. قالب Pagination و Error Response را مطابق قرارداد پیاده‌سازی کند.
5. تغییرات Breaking را فقط پس از ثبت در Changelog و هماهنگی دو تیم مصرف کند.

## جریان تحویل API

ترتیب پیشنهادی وضعیت هر Endpoint:

```text
Draft
→ Contract Ready
→ Backend Implemented
→ Backend Tested
→ Deployed to Dev
→ Frontend Integrated
→ QA Accepted
→ Released
```

Frontend فقط Endpointهایی را شروع می‌کند که حداقل در وضعیت `Contract Ready` باشند.

## قواعد Pull Request

هر Pull Request باید متناسب با نوع تغییر شامل موارد زیر باشد:

- شرح مسئله و دلیل تغییر
- فایل‌ها و Endpointهای تحت تأثیر
- نتیجه‌ی Test و Lint
- وضعیت Migration
- وضعیت قرارداد OpenAPI
- بررسی Authentication، Role و Scope
- ریسک‌ها و Breaking Changeها
- مراحل دقیق بازتولید یا تست

## مالکیت مسیرها

| مسیر | مالک اصلی |
|---|---|
| `Backend/` | Backend Team |
| `Frontend/` | Frontend Team |
| `contracts/` | Backend با Review مشترک Frontend |
| `docs/` | مشترک |
| `.github/` | مسئول فنی Repository |

تغییر فایل‌های مشترک باید با Review تیم یا مسئول تحت تأثیر انجام شود.
