# راهنمای اتصال Frontend به Backend هم‌آموز

این سند قرارداد اجرایی بین Frontend و Backend را مشخص می‌کند. هدف آن جلوگیری از پیاده‌سازی حدسی Endpointها، پراکندگی Headerها، ناسازگاری Typeها و اختلاف رفتار در مدیریت خطا است.

## 1. منبع حقیقت قرارداد

ترتیب مرجع برای پیاده‌سازی Frontend:

1. فایل Commit‌شده‌ی `contracts/openapi.yaml`
2. Schema زنده‌ی Backend در `/api/v1/schema/`
3. Swagger در `/api/v1/docs/`
4. ReDoc در `/api/v1/redoc/`
5. سابقه‌ی تغییرات در `contracts/API_CHANGELOG.md`

تا پیش از ادغام Backend در `main`، قرارداد جاری از این مسیر خوانده می‌شود:

- [`contracts/openapi.yaml` در backend/mvp-bootstrap](https://github.com/leonardo0231/hamamooz-platform/blob/backend/mvp-bootstrap/contracts/openapi.yaml)

اگر Schema زنده و فایل Commit‌شده با هم متفاوت باشند، Integration متوقف می‌شود تا Backend قرارداد را مجدداً تولید و Commit کند. Frontend نباید یکی از دو نسخه را به‌صورت سلیقه‌ای انتخاب کند.

فایل OpenAPI نباید دستی اصلاح شود.

## 2. Base URL

محیط توسعه‌ی محلی:

```text
http://localhost:8000/api/v1/
```

Base URL باید از Environment Configuration دریافت شود و داخل Component، Hook، Store یا Service هاردکد نشود.

نمونه‌ی مفهومی:

```text
API_BASE_URL=http://localhost:8000/api/v1/
```

نام دقیق متغیر محیطی به تکنولوژی Frontend بستگی دارد، اما باید فقط یک منبع مرکزی داشته باشد.

## 3. API Client مرکزی

تمام درخواست‌ها باید از یک API Client مشترک عبور کنند. Componentها نباید مستقیماً Token، Scope Header، Refresh Token یا Error Mapping را مدیریت کنند.

API Client مرکزی مسئول موارد زیر است:

- افزودن `Authorization`
- افزودن Scope فعال
- افزودن `X-Request-ID`
- مدیریت Refresh Token
- جلوگیری از Refresh هم‌زمان تکراری
- Parse کردن Pagination
- Normalize کردن Error Response
- لغو Requestهای بلااستفاده در صورت نیاز
- ثبت Log فنی بدون افشای Token یا اطلاعات حساس

## 4. جریان Authentication

### دریافت Token

```http
POST /api/v1/auth/token/
Content-Type: application/json
```

```json
{
  "username": "teacher1",
  "password": "password"
}
```

### دریافت اطلاعات کاربر

```http
GET /api/v1/auth/me/
Authorization: Bearer <access-token>
```

Frontend باید نقش‌ها، سازمان‌ها، شعب مجاز و اطلاعات کاربر را از این Endpoint دریافت کند و نباید آن‌ها را از محتوای ظاهری Token یا داده‌ی Hardcode شده استنتاج کند.

### تمدید Token

```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json
```

اگر چند Request هم‌زمان پاسخ `401` دریافت کردند، فقط یک Refresh Request اجرا می‌شود. سایر Requestها تا نتیجه‌ی همان عملیات منتظر می‌مانند و پس از موفقیت تکرار می‌شوند.

### Logout

```http
POST /api/v1/auth/logout/
Authorization: Bearer <access-token>
```

پس از Logout، Access Token، Refresh Token، اطلاعات کاربر و Scope انتخاب‌شده باید از State مربوط به Session پاک شوند. Tokenها نباید در Log، Error Monitoring یا پیام‌های UI نمایش داده شوند.

## 5. Headerهای عمومی

### Authorization

```http
Authorization: Bearer <access-token>
```

### Scope شعبه

```http
X-School-ID: <school-uuid>
```

### Scope مجموعه

```http
X-Organization-ID: <organization-uuid>
```

### شناسه‌ی رهگیری

```http
X-Request-ID: <uuid>
```

قواعد Scope:

- برای عملیات Write، کاربران غیر `system_admin` باید Scope صریح ارسال کنند.
- `X-School-ID` و `X-Organization-ID` نباید بدون نیاز هم‌زمان ارسال شوند.
- UUID نامعتبر یا Scope غیرمجاز می‌تواند پاسخ `403` ایجاد کند.
- Scope فعال باید در State مرکزی نگهداری شود.
- Componentها نباید Headerهای Scope را به‌صورت جداگانه بسازند.
- با تغییر Organization یا School، Cache و Queryهای وابسته باید Invalidated شوند.

## 6. Pagination

قالب استاندارد پاسخ List Endpointها:

```json
{
  "count": 120,
  "next": "http://localhost:8000/api/v1/students/?page=2",
  "previous": null,
  "results": []
}
```

پارامترهای رایج:

```text
page
page_size
search
ordering
```

Frontend باید آیتم‌ها را از `results` بخواند و `count` را برای تعداد کل استفاده کند. وجود `next` و `previous` باید براساس قرارداد همان Endpoint بررسی شود، نه براساس حدس مشترک برای همه‌ی APIها.

## 7. قالب خطا

قالب استاندارد خطا:

```json
{
  "error": {
    "code": "validation_error",
    "detail": {
      "field": [
        "message"
      ]
    },
    "request_id": "uuid"
  }
}
```

Frontend باید حداقل این رفتارها را داشته باشد:

| Status | رفتار مورد انتظار |
|---|---|
| `400` | نمایش خطای Validation و نگاشت خطاهای Field |
| `401` | اجرای Refresh و انتقال به Login در صورت شکست |
| `403` | نمایش عدم دسترسی یا Scope نامعتبر |
| `404` | نمایش نبود داده یا خارج بودن داده از Scope |
| `409` | نمایش تعارض داده، State یا Workflow |
| `429` | توقف Retry سریع و رعایت محدودیت درخواست |
| `503` | نمایش عدم آمادگی موقت سرویس و امکان Retry |
| Network Error | حفظ داده‌ی فرم و ارائه‌ی Retry |

`request_id` باید در گزارش Bug و پیام پشتیبانی فنی حفظ شود، اما نمایش آن به کاربر نهایی فقط در بخش جزئیات فنی انجام می‌شود.

## 8. Typeها و API Client تولیدشده

Frontend باید Typeها را از OpenAPI تولید یا حداقل با آن اعتبارسنجی کند.

قواعد:

- Type دستی نباید قرارداد OpenAPI را Override کند.
- Enumها باید از Schema استخراج شوند.
- Fieldهای Optional و Nullable از هم تفکیک شوند.
- Responseهای Paginated باید Generic مشترک داشته باشند.
- Client تولیدشده در یک لایه‌ی Adapter استفاده شود تا Componentها به جزئیات ابزار تولید وابسته نشوند.
- تغییر فایل OpenAPI باید Diff Typeها و Client را در Pull Request مشخص کند.

## 9. Endpointهای شروع Frontend

جریان پایه‌ی Sprint اول:

```text
POST auth/token/
GET auth/me/
GET organizations/
GET schools/
GET dashboard/summary/
```

خروجی مورد انتظار:

```text
Login
→ دریافت اطلاعات کاربر
→ انتخاب سازمان یا شعبه
→ ارسال Scope Header
→ نمایش Dashboard
```

تا زمان پایدار شدن این جریان، توسعه‌ی صفحات وابسته مانند دانش‌آموز، نمره، حضور و غیاب و گزارش نباید روی قراردادهای حدسی شروع شود.

## 10. Definition of Contract Ready

یک Endpoint زمانی `Contract Ready` است که همه‌ی موارد زیر مشخص باشند:

- Method و Path
- Authentication و Roleهای مجاز
- Scope مورد نیاز
- Path، Query و Header Parameterها
- Request Body و Validation
- Success Response
- Error Response و Status Codeها
- Pagination در صورت وجود
- Enumها، Optionalها و Nullableها
- نمونه‌ی Request/Response در Schema
- ثبت تغییر در `API_CHANGELOG.md`

وجود Endpoint در Swagger به‌تنهایی به معنی آماده بودن برای Integration نیست.

## 11. فرآیند تغییر API

Backend برای هر تغییر Contract باید:

1. تغییر را در کد پیاده‌سازی کند.
2. تست‌های Permission، Scope و Validation را اضافه یا اصلاح کند.
3. OpenAPI را مجدداً تولید کند.
4. Diff قرارداد را Review کند.
5. `contracts/API_CHANGELOG.md` را به‌روزرسانی کند.
6. Breaking Change را صریح علامت بزند.
7. محیط Development را به‌روزرسانی کند.

Frontend باید:

1. Diff فایل OpenAPI را بررسی کند.
2. Typeها و Client را بازتولید کند.
3. Compile و Test را اجرا کند.
4. Error Stateها را بررسی کند.
5. وضعیت Integration را در Pull Request ثبت کند.

وضعیت پیشنهادی Endpoint:

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

## 12. Breaking Change

موارد زیر Breaking Change محسوب می‌شوند مگر اینکه سازگاری قبلی حفظ شود:

- حذف یا تغییر نام Endpoint
- تغییر HTTP Method
- حذف یا Required شدن یک Field
- تغییر Type یا Enum
- تغییر ساختار Response
- تغییر Permission یا Scope
- تغییر معنای Status Code
- تغییر Pagination

Breaking Change باید قبل از Merge با Frontend هماهنگ، در Changelog ثبت و برای آن مسیر Migration یا نسخه‌بندی مشخص شود.

## 13. گزارش Bug مرتبط با API

هر Bug Report باید شامل این اطلاعات باشد:

- Environment
- Endpoint و Method
- Request Headers بدون Token کامل
- Request Payload با حذف اطلاعات حساس
- Response Status
- Response Body
- `request_id`
- نقش کاربر
- Organization یا School انتخاب‌شده
- زمان تقریبی رخداد
- مراحل بازتولید
- رفتار مورد انتظار و رفتار واقعی

گزارش‌هایی مانند «API کار نمی‌کند» بدون این اطلاعات برای بررسی فنی کافی نیستند.

## 14. چک‌لیست Frontend Pull Request

- [ ] Endpoint در OpenAPI وجود دارد.
- [ ] Typeها از قرارداد تولید یا با آن تطبیق داده شده‌اند.
- [ ] Base URL هاردکد نشده است.
- [ ] Token و Scope در API Client مرکزی مدیریت می‌شوند.
- [ ] `401`، `403`، `409` و Network Error پوشش داده شده‌اند.
- [ ] Loading، Empty و Error State وجود دارند.
- [ ] اطلاعات حساس Log نمی‌شوند.
- [ ] تغییر Breaking یا اختلاف Schema ثبت شده است.
- [ ] Test یا مراحل Manual Test در PR نوشته شده است.
