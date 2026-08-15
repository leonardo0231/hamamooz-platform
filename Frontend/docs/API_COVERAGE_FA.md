# پوشش API در Frontend جدید

مرز ارتباط با Backend در `src/core/api.js` متمرکز است. آدرس پایه به‌صورت پیش‌فرض `/api/v1/` است و می‌تواند با `window.__HAMAMOOZ_CONFIG__` در زمان اجرا تغییر کند.

## Endpointهای متصل

| قابلیت | Endpoint | مصرف UI |
|---|---|---|
| ورود | `POST /api/v1/auth/token/` | صفحه ورود |
| بازیابی نشست | `POST /api/v1/auth/token/refresh/` و `GET /api/v1/auth/me/` | bootstrap برنامه |
| خروج | `POST /api/v1/auth/logout/` | منوی کاربر |
| داشبورد مدیر | `GET /api/v1/dashboard/manager/` | داشبورد |
| فهرست دانش‌آموزان | `GET /api/v1/students/` | صفحه دانش‌آموزان |
| پرونده ۳۶۰ | چهار endpoint `summary`، `academics`، `attendance` و `evaluations` زیر `/students/{id}/360/` | پرونده دانش‌آموز |
| هشدارها | `GET /api/v1/attendance-alerts/` | مرکز هشدارها |
| منابع مدیریتی | `GET /api/v1/{tag}/` | صفحات عمومی مدیریت |

## قواعد امنیتی و پایداری

- Access token فقط در حافظه نگه‌داری می‌شود؛ refresh token بسته به گزینه «مرا به خاطر بسپار» در `sessionStorage` یا `localStorage` قرار می‌گیرد.
- refresh هم‌زمان deduplicate می‌شود و درخواست شکست‌خورده فقط یک بار تکرار می‌شود.
- `X-Request-ID`، `X-School-ID` یا `X-Organization-ID` در مرز API اضافه می‌شوند.
- timeout، خطای شبکه، خطاهای HTTP و field errorها به `ApiError` یکنواخت تبدیل می‌شوند.
- حالت `?demo=1` هیچ API تولیدی را صدا نمی‌زند و فقط برای بازبینی بصری با داده نمونه است.

تمام endpointهای بالا با `contracts/openapi.yaml` تطبیق داده شده‌اند. گسترش عملیات write باید همراه تست قرارداد و stateهای pending/success/error در UI انجام شود.
