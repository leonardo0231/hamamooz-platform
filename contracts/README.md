# API Contracts

این پوشه قرارداد رسمی بین Backend و Frontend سامانه هم‌آموز را نگهداری می‌کند.

## فایل‌ها

- `openapi.yaml`: قرارداد ماشین‌خوان API
- `API_CHANGELOG.md`: سابقه تغییرات API

## منبع حقیقت

فایل `openapi.yaml` باید از کد جاری Backend تولید شود:

```bash
cd Backend
./scripts/generate_openapi.sh ../contracts/openapi.yaml
```

فایل OpenAPI نباید دستی ویرایش شود.

## مسئولیت Backend

هر تغییر در موارد زیر نیازمند تولید مجدد OpenAPI است:

- Endpoint
- HTTP Method
- Request Body
- Response Body
- Query Parameter
- Path Parameter
- Header
- Permission
- Status Code
- Pagination
- Enum
- Nullability

## مسئولیت Frontend

Frontend باید Typeها و API Client خود را براساس همین قرارداد تولید یا اعتبارسنجی کند.

Frontend نباید ساختار Response را از روی حدس یا پیام‌های غیررسمی پیاده‌سازی کند.
