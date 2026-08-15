# گزارش پیاده‌سازی Frontend مرجع

## نتیجه

Frontend قدیمیِ مبتنی بر رندر دستی DOM با یک برنامه component-based بر پایه Preact 10.29.8 و HTM 3.1.1 جایگزین شده است. طراحی جدید RTL و واکنش‌گراست و زبان بصری تصاویر مرجع را در یک سیستم یکپارچه بازسازی می‌کند: زمینه روشن، سایدبار سرمه‌ای ثابت در سمت راست، رنگ تأکیدی بنفش، کارت‌های سفید کم‌سایه و نمودارهای سبک.

## نگاشت تصاویر مرجع

| الگوی مرجع | پیاده‌سازی |
|---|---|
| داشبورد مدیر و KPIها | `/` با کارت‌های آماری، روند عملکرد، مقایسه پایه‌ها و پیگیری فوری |
| فهرست و پرونده دانش‌آموز | `/students` و `/students/:id` با پروفایل ۳۶۰ درجه |
| مرکز هشدار دو ستونه | `/alerts` با فیلتر، فهرست هشدار و جزئیات انتخاب‌شده |
| ناوبری سرمه‌ای/بنفش | Shell مشترک تمام صفحات اصلی |
| چگالی اطلاعات طرح‌های تحلیلی | جدول دانش‌آموزان، KPIهای فشرده و نمودارهای بدون کتابخانه سنگین |

## معماری

| لایه | مسیر | مسئولیت |
|---|---|---|
| bootstrap و routing | `src/main.js`, `src/core/router.js` | route matching، auth guard و composition صفحه |
| state و session | `src/core/store.js` | نشست، scope و وضعیت سایدبار |
| API adapter | `src/core/api.js` | JWT refresh، timeout، scope headers و خطای یکنواخت |
| UI primitives | `src/components/ui.js` | کارت، KPI، badge، state و table shell |
| نمودار | `src/components/charts.js` | line/bar/donut با SVG/CSS و بدون dependency اضافی |
| shell | `src/components/shell.js` | header، navigation، mobile drawer و skip link |
| صفحات | `src/pages/` | dashboard، students، student 360، alerts و صفحات عمومی |
| design system | `src/styles/` | tokenها، componentها، صفحه‌ها و breakpointها |

## تصمیم فریم‌ورک

Preact به‌جای renderer اختصاصی انتخاب شد تا component lifecycle، hookها و composition استاندارد فراهم شود و در عین حال حجم runtime کوچک بماند. Preact و HTM با license خود در `src/vendor/` نگه‌داری می‌شوند؛ بنابراین build و اجرای production به CDN یا package registry وابسته نیست. SHA-256 بسته رسمی Preact استفاده‌شده:

```text
b18cb0a457f3d43c7bb30391a74ade7d13e03bc6e77915e061c70c0fe1123299
```

## واکنش‌گرایی و دسترس‌پذیری

- Desktop: سایدبار ثابت راست و gridهای چندستونه.
- Tablet: کاهش ستون‌ها و تبدیل layoutهای تحلیلی به grid دو ستونه.
- Mobile: drawer قابل باز و بسته‌شدن، کارت‌های تک‌ستونه و جدول اسکرول‌پذیر.
- `dir="rtl"` و `lang="fa"` در document، focus ring واضح، skip link، label برای جست‌وجو و دکمه‌ها و احترام به `prefers-reduced-motion`.

## حالت‌های UI

صفحات داده‌محور stateهای loading، error، empty و success را از hook مشترک دریافت می‌کنند. داده‌های نمونه فقط در `?demo=1` فعال می‌شوند و حالت production به API واقعی متصل است.

## کنترل کیفیت

- `npm run lint`: syntax و hygiene فایل‌های source.
- `npm test`: routeها، design tokenها، داده نمونه، امنیت storage و production build.
- `npm run build`: خروجی self-contained در `dist/`.
- `git diff --check`: کنترل whitespace و patch integrity.

بازبینی پیکسلی در مرورگر cloud به‌دلیل ممنوعیت دسترسی آن محیط به localhost ممکن نبود؛ بنابراین تأیید نهایی بصری باید از artifact یا محیط preview انجام شود.
