# Frontend هم‌آموز

رابط وب Production سامانه مدیریت آموزشی هم‌آموز. این Frontend مستقیماً از قرارداد رسمی `contracts/openapi.yaml` استفاده می‌کند و هیچ داده‌ی Mock یا Endpoint حدسی ندارد.

## Stack

- TypeScript 5 با تنظیمات Strict
- Browser ES Modules و Dynamic Import برای Route-level Code Splitting
- Router، Store و API Client ماژولار بدون وابستگی Runtime
- CSS Design System اختصاصی، RTL و Responsive
- Node.js Build/Preview scripts
- تست‌های داخلی Node Test Runner

پروژه‌ی قبلی در Branch فرانت‌اند فقط README داشت؛ بنابراین این پیاده‌سازی در مسیر رسمی `Frontend/` همان Monorepo ساخته شده است.

## نیازمندی‌ها

- Node.js 20 یا جدیدتر
- npm
- Backend هم‌آموز با قرارداد هماهنگ
- Python 3 و PyYAML فقط برای بازتولید Catalog از OpenAPI

## نصب و تنظیم محیط

```bash
cd Frontend
npm install
cp .env.example .env
```

مقادیر `.env`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api/v1/
VITE_APP_NAME=هم‌آموز
VITE_REQUEST_TIMEOUT_MS=20000
```

`VITE_API_BASE_URL` باید به `/api/v1/` ختم شود. فایل `.env` در Git Commit نمی‌شود.

## اجرای Development

```bash
npm run dev
```

برنامه روی `http://localhost:5173` اجرا می‌شود. این دستور Build اولیه را انجام می‌دهد، تغییرات TypeScript و فایل‌های استاتیک را Watch می‌کند و Preview Server دارای SPA fallback را فعال نگه می‌دارد.

Backend باید Origin فرانت‌اند را در `DJANGO_CORS_ALLOWED_ORIGINS` مجاز کند. برای Development مقدار `http://localhost:5173` و برای اجرای `npm run preview` مقدار `http://localhost:4173` لازم است؛ در Production باید Origin واقعی Deployment ثبت شود.

## کنترل کیفیت

```bash
npm run typecheck
npm run lint
npm test
```

## Build نسخه Production

```bash
npm run build
```

خروجی در `Frontend/dist/` ساخته می‌شود.

## اجرای Production Build

```bash
npm run preview
```

Preview روی `http://localhost:4173` اجرا می‌شود. در محیط واقعی باید `dist/` توسط Nginx، Caddy، CDN یا Static Hosting سرو شود و تمام Routeهای ناشناخته به `index.html` برگردند.

نمونه‌ی Nginx:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

## بازتولید قرارداد Frontend

پس از تغییر رسمی OpenAPI:

```bash
cd Frontend
npm run generate:api
npm run typecheck
npm test
```

این دستور فایل‌های زیر را از `contracts/openapi.yaml` می‌سازد:

- `src/api/generated/catalog.json`
- `src/api/generated/catalog.ts`

فایل OpenAPI در Frontend ویرایش نمی‌شود.

اگر شاخه‌ی Frontend مستقل Checkout شده و پوشه‌ی `contracts/` کنار آن موجود نیست،
مسیر قرارداد Backend را صریح بدهید:

```bash
HAMAMOOZ_OPENAPI_SOURCE=/path/to/backend/contracts/openapi.yaml npm run generate:api
```

## Authentication و Session

- Access Token فقط در حافظه نگهداری می‌شود.
- Refresh Token برای نشست عادی در `sessionStorage` نگهداری می‌شود.
- فقط با انتخاب «مرا به خاطر بسپار» Refresh Token در `localStorage` نگهداری می‌شود؛ این رفتار به دلیل قرارداد JWT فعلی Backend است.
- اعتبار نشست با `GET auth/me/` بررسی می‌شود.
- درخواست‌های هم‌زمان 401 فقط یک Refresh مشترک ایجاد می‌کنند.
- با Logout، Tokenها، User State و Scope فعال پاک می‌شوند.

## Scope و Permission

API Client به‌صورت مرکزی Headerهای زیر را مدیریت می‌کند:

- `Authorization`
- `X-School-ID`
- `X-Organization-ID`
- `X-Request-ID`

Route Guard و Role Guard در Client وجود دارد؛ کنترل نهایی Permission همچنان متعلق به Backend است.

## مستندات تکمیلی

- [گزارش پیاده‌سازی](docs/IMPLEMENTATION_REPORT_FA.md)
- [پوشش API و صفحات](docs/API_COVERAGE_FA.md)
