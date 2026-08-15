# فرانت‌اند هم‌آموز

نسخه دوم رابط کاربری سامانه هوشمند مدرسه؛ بازطراحی‌شده بر اساس داشبوردهای مدیریتی RTL با تمرکز بر پایش، هشدار و پرونده ۳۶۰ درجه دانش‌آموز.

## معماری

- Preact 10.29.8 با Component و Hook؛ به‌صورت self-hosted و بدون CDN
- HTM برای templateهای امن و خوانا بدون toolchain سنگین
- Browser ES Modules و build قطعی بدون وابستگی شبکه
- API Client مرکزی با JWT refresh، timeout، error normalization و scope headers
- Design system اختصاصی فارسی با Vazirmatn/Estedad، RTL و responsive layout
- Node Test Runner برای route، امنیت، fixture، design contract و build

فایل‌های Third-party در `src/vendor/` همراه license نگهداری شده‌اند. نسخه Preact با digest رسمی release تطبیق داده شده است.

## اجرا

پیش‌نیاز فقط Node.js 20 یا جدیدتر است و نصب package لازم نیست:

```bash
cd Frontend
npm run dev
```

برنامه روی `http://localhost:5173` اجرا می‌شود. درخواست‌های `/api/` در حالت development به Backend روی پورت `8000` proxy می‌شوند.

برای مشاهده رابط بدون Backend:

```text
http://localhost:5173/?demo=1
```

حالت demo فقط با query string یا کلید `hamamooz.demo` فعال می‌شود و در مسیر عادی production استفاده نمی‌شود.

## کنترل کیفیت

```bash
npm run lint
npm test
npm run build
```

خروجی production در `dist/` قرار می‌گیرد. برای بررسی خروجی:

```bash
npm run preview
```

## مسیرهای اصلی

- `/` داشبورد مدیریتی
- `/students` فهرست دانش‌آموزان
- `/students/:id` پرونده ۳۶۰ درجه
- `/performance` عملکرد آموزشی
- `/attendance` حضور و غیاب
- `/alerts` مرکز هشدارها و پیگیری
- `/suggestions` پیشنهادهای هوشمند
- `/reports` گزارش‌ساز
- مسیرهای مدیریت داده، کاربر، نقش، تنظیمات و پورتال

## اتصال Backend

Base URL پیش‌فرض `/api/v1/` است تا در Docker و Nginx همان origin استفاده شود. برای محیطی متفاوت می‌توان پیش از `main.js` مقدار runtime زیر را تعیین کرد:

```js
window.__HAMAMOOZ_CONFIG__ = {
  apiBaseUrl: 'https://example.com/api/v1/',
  requestTimeoutMs: 20000,
};
```

API Client به‌صورت مرکزی Headerهای `Authorization`، `X-School-ID`، `X-Organization-ID` و `X-Request-ID` را مدیریت می‌کند. Access token فقط در حافظه است؛ refresh token مطابق انتخاب «مرا به خاطر بسپار» در sessionStorage یا localStorage نگهداری می‌شود.

منبع حقیقت قرارداد همچنان `contracts/openapi.yaml` است. تغییر Endpoint باید ابتدا در قرارداد و Backend اعمال و سپس adapter متناظر در `src/core/api.js` به‌روزرسانی شود.
