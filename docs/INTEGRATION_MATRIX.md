# ماتریس یکپارچه‌سازی Backend و Frontend

این جدول وضعیت Contract، پیاده‌سازی Backend، اتصال Frontend و پذیرش QA را ثبت می‌کند.

| جریان | Endpoint | Contract | Backend | Frontend | QA |
| --- | --- | --- | --- | --- | --- |
| ورود | `POST /api/v1/auth/token/` | Contract Ready | Backend Tested | Not Started | Not Started |
| اطلاعات کاربر | `GET /api/v1/auth/me/` | Contract Ready | Backend Tested | Not Started | Not Started |
| سازمان‌ها | `GET /api/v1/organizations/` | Contract Ready | Backend Tested | Not Started | Not Started |
| شعب | `GET /api/v1/schools/` | Contract Ready | Backend Tested | Not Started | Not Started |
| داشبورد | `GET /api/v1/dashboard/summary/` | Contract Ready | Backend Tested | Not Started | Not Started |

## قواعد به‌روزرسانی

- منبع Contract فایل `contracts/openapi.yaml` است.
- تغییر Endpoint بدون تولید مجدد Contract مجاز نیست.
- وضعیت Frontend فقط پس از اتصال واقعی به API تغییر می‌کند.
- وضعیت QA فقط پس از تست Role، Scope و Error State تغییر می‌کند.
