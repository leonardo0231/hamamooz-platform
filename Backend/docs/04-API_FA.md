# راهنمای API نسخه ۱

Base URL: `/api/v1/`

تمام Endpointها به‌جز Health و Login به JWT نیاز دارند. مرجع دقیق request/response، Schema زنده `/api/v1/schema/` است.

## قرارداد عمومی

### Headerها

```http
Authorization: Bearer <access-token>
X-School-ID: <school-uuid>
X-Organization-ID: <organization-uuid>
X-Request-ID: <optional-client-request-id>
```

- برای Read، Scope header اختیاری است و نبود آن به معنی همه حوزه‌های مجاز کاربر است.
- برای Write، کاربر غیر `system_admin` باید School یا Organization صریح بفرستد.
- ارسال هم‌زمان دو Scope فقط وقتی مجاز است که شعبه متعلق به همان مجموعه باشد.
- `X-Request-ID` ورودی تا ۶۴ نویسه حفظ می‌شود؛ اگر ارسال نشود سامانه UUID جدید می‌سازد و در پاسخ برمی‌گرداند.

### صفحه‌بندی و Query

Listها پاسخ صفحه‌بندی‌شده دارند:

```json
{
  "count": 120,
  "next": "...page=2",
  "previous": null,
  "results": []
}
```

پارامترهای عمومی: `page`, `page_size` تا سقف ۲۰۰، `search`, `ordering` و filterهای اعلام‌شده در Schema.

### قالب خطا

```json
{
  "error": {
    "code": "validation_error",
    "detail": {"field": ["message"]},
    "request_id": "..."
  }
}
```

کدهای رایج: 400 validation، 401 token، 403 Scope/role، 404 resource خارج از QuerySet مجاز، 429 throttle و 503 readiness.

## احراز هویت و کاربران

| Method | Endpoint | کاربرد |
|---|---|---|
| POST | `auth/token/` | ورود با username یا email و دریافت token |
| POST | `auth/token/refresh/` | چرخش Refresh token |
| POST | `auth/logout/` | blacklist Refresh token |
| GET | `auth/me/` | کاربر و RoleAssignmentهای فعال |
| CRUD محدود | `users/` | مدیریت کاربر؛ Delete غیرفعال است |
| POST | `users/{id}/change_password/` | تغییر رمز خود یا reset کنترل‌شده |
| POST | `users/{id}/deactivate/` | غیرفعال‌سازی و revoke tokenها |
| CRUD | `role-assignments/` | تخصیص نقش در Scope مجاز |

## ساختار سازمانی

| Resource | Endpoint | عملیات |
|---|---|---|
| مجموعه | `organizations/` | CRUD با محدودیت نقش |
| شعبه | `schools/` | CRUD |
| سال تحصیلی | `academic-years/` | CRUD |
| نوبت | `terms/` | CRUD |
| پایه | `grade-levels/` | CRUD |
| کلاس | `classes/` | CRUD و کنترل ظرفیت |

## دانش‌آموز و ثبت‌نام

| Method | Endpoint | کاربرد |
|---|---|---|
| CRUD | `students/` | پرونده دانش‌آموز |
| POST | `students/{id}/guardians/` | اتصال ولی |
| CRUD | `guardians/` | مدیریت ولی |
| GET/POST | `enrollments/` | فهرست/ایجاد ثبت‌نام |
| POST | `enrollments/{id}/change-class/` | تغییر کلاس تاریخ‌مند |
| POST | `enrollments/{id}/transfer/` | انتقال شعبه |
| POST | `enrollments/{id}/change-status/` | ترک‌تحصیل/فارغ‌التحصیلی و سایر وضعیت‌ها |

نمونه تغییر کلاس:

```http
POST /api/v1/enrollments/{id}/change-class/
Content-Type: application/json

{"class_section":"<uuid>","reason":"اصلاح کلاس‌بندی"}
```

نمونه انتقال:

```json
{
  "school": "<target-school-uuid>",
  "grade_level": "<grade-uuid>",
  "class_section": "<target-class-uuid>",
  "student_number": "2001",
  "transfer_date": "2026-11-01",
  "reason": "جابجایی محل سکونت"
}
```

کاربر باید در مقصد نیز نقش نوشتن داشته باشد.

## آموزش و نمره

منابع: `subjects/`, `grade-subjects/`, `course-offerings/`, `assessment-types/`, `assessments/`, `scores/`, `calculation-policies/`.

Actionها:

| Method | Endpoint | کاربرد |
|---|---|---|
| GET | `course-offerings/{id}/results/` | نتیجه‌های درس |
| GET | `assessments/{id}/scores/` | roster نمره |
| POST | `assessments/{id}/scores/bulk/` | ثبت گروهی |
| POST | `assessments/{id}/submit/` | ارسال برای بررسی |
| POST | `assessments/{id}/approve/` | تأیید |
| POST | `assessments/{id}/reject/` | رد همراه دلیل |
| POST | `assessments/{id}/lock/` | قفل و صف محاسبه |
| POST | `scores/{id}/correct-locked/` | اصلاح رسمی نمره قفل‌شده |

```json
{
  "entries": [
    {"enrollment":"<uuid>","value":"18.50","status":"present","note":""},
    {"enrollment":"<uuid>","value":null,"status":"excused_absent","note":"گواهی پزشکی"}
  ]
}
```

اصلاح قفل‌شده فقط برای reviewer، همراه دلیل حداقل پنج نویسه و بدون Unlock کردن Assessment انجام می‌شود.

## حضور و غیاب

منابع: `attendance-sessions/`, `attendance-records/`, `attendance-policies/`, `attendance-alerts/`, `parent-notifications/`, `attendance-reports/`.

Actionهای اصلی:

| Method | Endpoint | کاربرد |
|---|---|---|
| GET | `attendance-sessions/{id}/roster/` | roster تاریخ‌مند |
| POST | `attendance-sessions/{id}/bulk-mark/` | ثبت گروهی draft |
| POST | `attendance-sessions/{id}/finalize/` | نهایی‌سازی roster کامل |
| POST | `attendance-sessions/{id}/cancel/` | لغو جلسه |
| POST | `attendance-records/{id}/correct/` | اصلاح رسمی |
| POST | `attendance-records/{id}/submit-excuse/` | ثبت عذر و مدارک |
| POST | `attendance-records/{id}/approve-excuse/` | تأیید عذر |
| POST | `attendance-records/{id}/reject-excuse/` | رد عذر |
| POST | `attendance-records/{id}/notify-guardians/` | ساخت اعلان |
| POST | `attendance-alerts/evaluate/` | ارزیابی Policy |
| POST | `attendance-alerts/{id}/acknowledge/` | مشاهده هشدار |
| POST | `attendance-alerts/{id}/resolve/` | رفع هشدار |
| POST | `parent-notifications/{id}/retry/` | retry اعلان ناموفق |
| GET | `attendance-reports/student/` | گزارش دانش‌آموز |
| GET | `attendance-reports/class/` | گزارش کلاس |
| GET | `attendance-reports/school/` | گزارش شعبه |
| POST | `attendance-reports/notify-guardians/` | اعلان گزارش بازه‌ای |

جزئیات Payloadها در `API_REFERENCE_FA.md` است.

## Import

```http
POST /api/v1/imports/
Content-Type: multipart/form-data

school=<uuid>
import_type=students|enrollments|scores
source_file=<xlsx>
```

نام و ترتیب ستون‌ها ثابت است. کل فایل قبل از Write اعتبارسنجی می‌شود. Job با `GET /imports/{id}/` Poll می‌شود و فقط Job ناموفق یا processing منقضی‌شده با `POST /imports/{id}/retry/` قابل تکرار است.

## گزارش کارنامه

پیش‌نمایش بدون آرشیو:

```http
POST /api/v1/reports/preview/
Content-Type: application/json

{"report_type":"student_report_card","term":"<uuid>","enrollment":"<uuid>"}
```

تولید رسمی همان Payload را به `POST /reports/` می‌فرستد. همه ارزیابی‌های درس‌های فعال باید وجود داشته و `locked` باشند. پس از `completed`:

```text
GET /api/v1/reports/{id}/download/
```

برای کلاس از `report_type=class_report_cards` و `class_section` استفاده می‌شود.

## Health و مستندات

| Endpoint | دسترسی | معنی |
|---|---|---|
| `health/live/` | عمومی | Process زنده است |
| `health/ready/` | عمومی | DB و Cache و بر اساس Settings، Broker/Storage آماده‌اند؛ Production هر چهار مورد را بررسی می‌کند |
| `schema/` | مطابق تنظیم drf-spectacular | OpenAPI جاری |
| `docs/` | UI | Swagger |
| `redoc/` | UI | ReDoc |
