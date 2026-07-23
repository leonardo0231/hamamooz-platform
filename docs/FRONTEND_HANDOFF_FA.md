# راهنمای اتصال Frontend به Backend هم‌آموز

## 1. Base URL

محیط توسعه محلی:

```text
http://localhost:8000/api/v1/
```

محیط Development Server باید از طریق متغیر محیطی به Frontend داده شود و نباید داخل کد Hardcode شود.

## 2. مستندات API

- Swagger: `/api/v1/docs/`
- ReDoc: `/api/v1/redoc/`
- OpenAPI Schema: `/api/v1/schema/`
- قرارداد Commit شده: `/contracts/openapi.yaml`

منبع اصلی ساختار Request و Response، فایل OpenAPI جاری است.

## 3. جریان ورود

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

Frontend باید اطلاعات کاربر، نقش‌ها، سازمان‌ها و شعب مجاز را از این Endpoint دریافت کند.

## 4. Headerهای عمومی

درخواست‌های احرازشده:

```http
Authorization: Bearer <access-token>
```

درخواست‌های مرتبط با شعبه:

```http
X-School-ID: <school-uuid>
```

درخواست‌های مرتبط با مجموعه:

```http
X-Organization-ID: <organization-uuid>
```

برای Trace کردن درخواست:

```http
X-Request-ID: <uuid>
```

برای عملیات Write، کاربران غیر `system_admin` باید Scope صریح ارسال کنند.

Frontend نباید `X-School-ID` یا `X-Organization-ID` را داخل هر Component به‌صورت جداگانه اضافه کند. این Headerها باید توسط API Client مرکزی اضافه شوند.

## 5. صفحه‌بندی

پاسخ List Endpointها:

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

Frontend باید داده‌های لیست را از `results` دریافت کند.

## 6. قالب خطا

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

رفتار Frontend:

- `400`: نمایش خطای Validation
- `401`: Refresh Token و در صورت شکست انتقال به Login
- `403`: نمایش عدم دسترسی یا Scope نامعتبر
- `404`: نمایش داده پیدا نشد یا داده خارج از Scope
- `409`: نمایش تعارض داده یا Workflow
- `429`: محدودکردن Retry
- `503`: نمایش عدم آمادگی موقت سرویس
- Network Error: نمایش Retry و حفظ اطلاعات فرم

## 7. Refresh Token

Frontend باید Refresh Token را فقط از طریق Endpoint زیر تمدید کند:

```http
POST /api/v1/auth/token/refresh/
```

اگر چند Request هم‌زمان پاسخ `401` دریافت کردند، فقط یک Refresh Request باید اجرا شود.

سایر Requestها باید تا نتیجه Refresh منتظر بمانند.

## 8. Logout

```http
POST /api/v1/auth/logout/
Authorization: Bearer <access-token>
```

پس از Logout، Access Token، Refresh Token و Scope انتخاب‌شده باید از حافظه Frontend پاک شوند.

## 9. Endpointهای Sprint اول

Frontend در Sprint اول فقط این جریان را پیاده‌سازی می‌کند:

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

تا زمان تکمیل این جریان، پیاده‌سازی صفحات دانش‌آموز، نمره، حضور و غیاب و گزارش شروع نمی‌شود.

## 10. تغییرات API

Backend موظف است قبل از تحویل Endpoint:

1. Endpoint را پیاده‌سازی کند.
2. تست Permission بنویسد.
3. OpenAPI را تولید کند.
4. `API_CHANGELOG.md` را به‌روزرسانی کند.
5. Endpoint را روی محیط Development اجرا کند.

Frontend فقط Endpointهایی را شروع می‌کند که حداقل در وضعیت `Contract Ready` باشند.

وضعیت‌های قابل استفاده:

```text
Draft
Contract Ready
Backend Implemented
Backend Tested
Deployed to Dev
Frontend Integrated
QA Accepted
Released
```

## 11. قواعد مالکیت فایل‌ها

Backend Team:

```text
Backend/
contracts/
Backend/docs/
```

Frontend Team:

```text
Frontend/
```

فایل‌های مشترک فقط با Review مسئول فنی تغییر می‌کنند.

## 12. گزارش Bug فرانت

هر Bug مرتبط با API باید شامل موارد زیر باشد:

- Endpoint
- Method
- Request Headers
- Request Payload
- Response Status
- Response Body
- Request ID
- نقش کاربر
- School یا Organization انتخاب‌شده
- مراحل بازتولید
