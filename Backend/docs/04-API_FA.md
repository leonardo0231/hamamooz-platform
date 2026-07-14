# راهنمای API نسخه ۱

Base URL: `/api/v1/`

تمام Endpointها به‌جز Health و Login به `Authorization: Bearer ...` نیاز دارند. برای انتخاب شعبه از `X-School-ID` استفاده کنید.

## احراز هویت

| Method | Endpoint | کاربرد |
|---|---|---|
| POST | `auth/token/` | Access/Refresh token و خلاصه کاربر |
| POST | `auth/token/refresh/` | چرخش Refresh token |
| POST | `auth/logout/` | Blacklist کردن Refresh token |
| GET | `auth/me/` | کاربر و نقش‌های فعال |
| POST | `users/{id}/change_password/` | تغییر رمز خود یا Reset کنترل‌شده |
| POST | `users/{id}/deactivate/` | غیرفعال‌سازی کاربر |

## منابع اصلی

| Resource | Endpoint |
|---|---|
| مجموعه/شعبه | `organizations/`, `schools/` |
| سال/نوبت/پایه/کلاس | `academic-years/`, `terms/`, `grade-levels/`, `classes/` |
| کاربر/نقش | `users/`, `role-assignments/` |
| دانش‌آموز/ولی/ثبت‌نام | `students/`, `guardians/`, `enrollments/` |
| درس و ارائه | `subjects/`, `grade-subjects/`, `course-offerings/` |
| ارزیابی و نمره | `assessment-types/`, `assessments/`, `scores/` |
| فرمول | `calculation-policies/` |
| Import | `imports/` |
| گزارش | `reports/` |
| داشبورد | `dashboard/summary/` |

همه Listها `page` و `page_size` تا سقف ۲۰۰ دارند و Filterهای دقیق هر Endpoint در Swagger آمده‌اند.

## ثبت گروهی نمره

```http
POST /api/v1/assessments/{assessment_id}/scores/bulk/
Authorization: Bearer <token>
X-School-ID: <uuid>
Content-Type: application/json

{
  "entries": [
    {"enrollment": "<uuid>", "value": "18.50", "status": "present", "note": ""},
    {"enrollment": "<uuid>", "value": null, "status": "excused_absent", "note": "گواهی پزشکی"}
  ]
}
```

سپس:

```text
POST assessments/{id}/submit/
POST assessments/{id}/approve/
POST assessments/{id}/reject/      {"reason":"..."}
POST assessments/{id}/lock/
```

پس از Lock، محاسبه کلاس در Queue قرار می‌گیرد. اصلاح استثنایی نمره قفل‌شده:

```http
POST /api/v1/scores/{score_id}/correct-locked/

{"value":"19","status":"present","note":"اصلاح","reason":"خطای ورود اولیه"}
```

این مسیر فقط برای Reviewer و با دلیل حداقل پنج نویسه فعال است و Assessment را از حالت قفل خارج نمی‌کند.

## تغییر کلاس و انتقال

```http
POST /api/v1/enrollments/{id}/change-class/
{"class_section":"<uuid>","reason":"اصلاح کلاس‌بندی"}
```

```http
POST /api/v1/enrollments/{id}/transfer/
{
  "school":"<target-school-uuid>",
  "grade_level":"<grade-uuid>",
  "class_section":"<target-class-uuid>",
  "student_number":"2001",
  "transfer_date":"2026-11-01",
  "reason":"جابجایی محل سکونت"
}
```

انتقال فقط وقتی مجاز است که کاربر به شعبه مقصد هم دسترسی داشته باشد.

## Import

```http
POST /api/v1/imports/
Content-Type: multipart/form-data

school=<uuid>
import_type=students|enrollments|scores
source_file=<xlsx>
```

سه قالب دقیق در `docs/import_templates/` قرار دارند. ترتیب یا نام ستون‌ها قابل تغییر نیست. اگر حتی یک ردیف خطا داشته باشد، هیچ ردیفی Commit نمی‌شود و خطاها در فیلد `errors` Job بازمی‌گردند.

## گزارش

پیش‌نمایش بدون آرشیو:

```http
POST /api/v1/reports/preview/
{"report_type":"student_report_card","term":"<uuid>","enrollment":"<uuid>"}
```

تولید آرشیوی همان Payload را به `POST /reports/` می‌فرستد. این مسیر رسمی تنها زمانی پذیرفته می‌شود که برای همه درس‌های فعال کلاس دست‌کم یک ارزیابی وجود داشته باشد و تمام ارزیابی‌ها `locked` باشند. وضعیت Job Poll می‌شود و پس از `completed`:

```text
GET /api/v1/reports/{id}/download/
```

برای کل کلاس از `report_type=class_report_cards` و `class_section` استفاده کنید.

## قالب خطا

```json
{
  "error": {
    "code": "validation_error",
    "detail": {"field": ["message"]},
    "request_id": "..."
  }
}
```

`X-Request-ID` ورودی حفظ می‌شود یا سامانه یک UUID می‌سازد و در پاسخ بازمی‌گرداند.
