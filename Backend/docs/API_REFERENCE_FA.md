# مرجع API حضور و غیاب

تمام مسیرها زیر `/api/v1/` هستند و از JWT و هدرهای tenant موجود پروژه استفاده می‌کنند.

## جلسات

| Method | Endpoint | کاربرد |
|---|---|---|
| GET/POST | `attendance-sessions/` | فهرست/ایجاد جلسه روزانه یا زنگ |
| GET/PATCH/DELETE | `attendance-sessions/{id}/` | مشاهده/ویرایش/حذف جلسه draft |
| GET | `attendance-sessions/{id}/roster/` | roster کلاس همراه رکوردهای فعلی |
| POST | `attendance-sessions/{id}/bulk-mark/` | ثبت یا اصلاح گروهی draft |
| POST | `attendance-sessions/{id}/finalize/` | نهایی‌سازی پس از تکمیل roster |
| POST | `attendance-sessions/{id}/cancel/` | لغو جلسه و خارج‌کردن از گزارش‌های فعال |

نمونه جلسه روزانه:

```json
{
  "school": "uuid",
  "academic_year": "uuid",
  "class_section": "uuid",
  "session_date": "2026-10-01",
  "scope": "daily",
  "starts_at": "08:00:00",
  "ends_at": "13:00:00"
}
```

نمونه جلسه زنگ:

```json
{
  "school": "uuid",
  "academic_year": "uuid",
  "class_section": "uuid",
  "term": "uuid",
  "course_offering": "uuid",
  "session_date": "2026-10-01",
  "scope": "period",
  "period_number": 2,
  "starts_at": "09:00:00",
  "ends_at": "10:00:00"
}
```

نمونه bulk:

```json
{
  "records": [
    {
      "enrollment": "uuid",
      "status": "present",
      "arrival_time": "08:12:00",
      "departure_time": "12:45:00"
    },
    {
      "enrollment": "uuid",
      "status": "absent_unexcused"
    }
  ]
}
```

## رکوردها و غیبت موجه

| Method | Endpoint | کاربرد |
|---|---|---|
| GET | `attendance-records/` | فهرست و فیلتر رکوردها |
| GET | `attendance-records/{id}/` | جزئیات، مدارک و revision history |
| POST | `attendance-records/{id}/correct/` | اصلاح رسمی همراه دلیل |
| POST | `attendance-records/{id}/submit-excuse/` | ثبت دلیل و حداکثر ۵ مدرک |
| POST | `attendance-records/{id}/approve-excuse/` | تأیید مسئول |
| POST | `attendance-records/{id}/reject-excuse/` | رد مسئول |
| POST | `attendance-records/{id}/notify-guardians/` | ایجاد اعلان برای والدین |

`submit-excuse` با `multipart/form-data` ارسال می‌شود:

```text
reason=گواهی پزشک
evidence_files=<file1>
evidence_files=<file2>
```

## Policy و هشدار

| Method | Endpoint | کاربرد |
|---|---|---|
| CRUD | `attendance-policies/` | سیاست شعبه/سال تحصیلی |
| GET | `attendance-alerts/` | هشدارهای قابل دسترسی |
| POST | `attendance-alerts/evaluate/` | محاسبه دستی یک policy |
| POST | `attendance-alerts/{id}/acknowledge/` | مشاهده‌شده |
| POST | `attendance-alerts/{id}/resolve/` | رفع دستی |

نمونه ارزیابی:

```json
{"policy": "uuid"}
```

## گزارش‌ها

| Method | Endpoint | پارامترها |
|---|---|---|
| GET | `attendance-reports/student/` | `enrollment`, `date_from`, `date_to`, `scope` |
| GET | `attendance-reports/class/` | `class_section`, `date_from`, `date_to`, `scope` |
| GET | `attendance-reports/school/` | `school`, `academic_year`, `date_from`, `date_to`, `scope` |
| POST | `attendance-reports/notify-guardians/` | Enrollment، بازه، scope و channels |

خروجی metrics شامل موارد زیر است:

```json
{
  "total_sessions": 20,
  "absence_count": 3,
  "excused_absence_count": 1,
  "unexcused_absence_count": 2,
  "late_count": 4,
  "early_leave_count": 1,
  "absence_percent": "15.00"
}
```

## اعلان والدین

| Method | Endpoint | کاربرد |
|---|---|---|
| GET | `parent-notifications/` | outbox و وضعیت ارسال |
| POST | `parent-notifications/{id}/retry/` | تلاش مجدد اعلان ناموفق |
