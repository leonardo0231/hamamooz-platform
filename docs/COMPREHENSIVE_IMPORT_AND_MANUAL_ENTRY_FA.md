# فایل جامع مدرسه و ثبت/ویرایش دستی

این سند رفتار رسمی Import جامع و مسیرهای ثبت دستی HamAmoz را بر اساس پیاده‌سازی `backend/comprehensive-manual-hardening` در تاریخ 2026-08-08 ثبت می‌کند.

## 1. اصل طراحی

دو مسیر ورود داده وجود دارد:

### Bulk

فقط با فایل جامع رسمی مدرسه:

```text
comprehensive_school
```

### Manual

از پنل:

```text
/manual-entry
```

نباید برای یک Domain دو API موازی با منطق متفاوت ساخته شود. Manual UI تا جای ممکن همان Domain endpointهای رسمی را استفاده می‌کند؛ فقط Monthly Evaluation به دلیل نیاز به upsert تدریجی و soft-delete امن Action اختصاصی دارد.

## 2. Template رسمی

فایل Backend:

```text
Backend/docs/import_templates/comprehensive_school_template.xlsx
```

Public download:

```http
GET /api/v1/imports/templates/comprehensive_school/
```

Filename پاسخ:

```text
comprehensive_school_template.xlsx
```

Content type:

```text
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
```

## 3. Sheetهای ورودی

Loader رسمی فقط سه Sheet ورودی را برای import domain می‌خواند:

```text
کلاس‌بندی
دانش‌آموزان
ثبت اطلاعات
```

Template می‌تواند Sheetهای راهنما/محاسباتی دیگری هم داشته باشد، ولی Contract importer بر همین سه Sheet ورودی تکیه می‌کند.

Headerها در row 4 بررسی می‌شوند.

## 4. کلاس‌بندی

Header دقیق:

```text
ردیف
کد مدرسه
سال تحصیلی
کد کلاس
نام کلاس
پایه تحصیلی
ظرفیت
```

Loader فعلی data rows این Sheet را در بازه row 5 تا 34 می‌خواند.

قواعد مهم:

- School code باید با Scope Job سازگار باشد.
- Academic year باید معتبر باشد.
- Class code کلید قابل اتکای Template است.
- Grade باید قابل resolve باشد.
- Capacity باید معتبر باشد.

Import Class را create/update می‌کند، ولی absence آن در فایل باعث delete نمی‌شود.

## 5. دانش‌آموزان

Header دقیق:

```text
ردیف
کد محلی
کد ملی
شماره دانش‌آموزی
نام
نام خانوادگی
جنسیت
تاریخ تولد
کد کلاس
```

Loader فعلی row 5 تا 104 را می‌خواند.

### local_code

`کد محلی` یک key داخل workbook برای اتصال Evaluation row به Student row است. این مقدار global student identity نیست.

### national_id

قانون hardened:

```text
exactly 10 digits
```

- رقم فارسی/عربی normalize می‌شود.
- مقدار کوتاه دیگر با `zfill` اصلاح نمی‌شود.
- صفر اول باید در فایل حفظ شود.
- ستون Excel بهتر است Text باشد.

### student_number

شماره دانش‌آموزی در Scope ثبت‌نام/مدرسه/سال باید با constraintهای Domain سازگار باشد.

### class_code

Student به Class row فایل متصل می‌شود و Enrollment مناسب ساخته/به‌روزرسانی می‌شود.

## 6. ثبت اطلاعات / Evaluation

Identity header دقیق شش ستون اول:

```text
ردیف
ماه
کد محلی
کد ملی
نام و نام خانوادگی
کد کلاس
```

Metricها از column 7 تا 80 هستند: **74 ستون**.

Header هر Metric باید با code مورد انتظار Catalog شروع شود. ترتیب Metricها نیز بررسی می‌شود.

## 7. ترتیب ماه‌ها

Mapping رسمی importer:

| month_no | عنوان |
|---:|---|
| 1 | تیر |
| 2 | مرداد |
| 3 | شهریور |
| 4 | مهر |
| 5 | آبان |
| 6 | آذر |
| 7 | دی |
| 8 | بهمن |
| 9 | اسفند |
| 10 | فروردین |
| 11 | اردیبهشت |
| 12 | خرداد |

Frontend Manual Evaluation نیز همین ترتیب را نمایش می‌دهد و `month_no` عددی می‌فرستد.

## 8. Catalog ارزیابی — 74 Metric

Framework:

```text
FRAMEWORK_VERSION = 1.0
```

Score range:

```text
0..5
```

Domainها:

| Prefix | Domain | Weight | Metric count | Code range |
|---|---|---:|---:|---|
| `EDU` | آموزشی | 20 | 10 | `EDU_01..EDU_10` |
| `DEV` | پرورشی | 15 | 10 | `DEV_01..DEV_10` |
| `CHR` | تربیتی | 15 | 10 | `CHR_01..CHR_10` |
| `DIS` | انضباطی | 15 | 8 | `DIS_01..DIS_08` |
| `CUL` | فرهنگی | 7 | 7 | `CUL_01..CUL_07` |
| `RES` | پژوهشی | 8 | 8 | `RES_01..RES_08` |
| `SPT` | ورزشی | 7 | 7 | `SPT_01..SPT_07` |
| `ART` | هنری | 6 | 7 | `ART_01..ART_07` |
| `PER` | مهارت‌های فردی | 7 | 7 | `PER_01..PER_07` |

مجموع Weightها = `100`.

مرجع عنوان کامل Metricها:

```text
Backend/hamamooz/apps/evaluations/catalog.py
GET /api/v1/monthly-evaluations/catalog/
```

Frontend نباید تعریف 74 Metric را hardcode کند.

## 9. Hardened Evaluation Identity Check

Parser اصلی Evaluation را با `local_code` متصل می‌کند. Hardened layer علاوه بر آن سه cell visible را از workbook نگه می‌دارد:

```text
national_id
full_name
class_code
```

اگر nonblank باشند:

- national id باید exact 10-digit و مساوی Student sheet باشد
- class code باید مساوی Student sheet باشد
- normalized full name باید مساوی Student sheet باشد

Mismatch قبل از write به Validation error تبدیل می‌شود.

## 10. Atomicity

Validation قبل از apply انجام می‌شود. اگر workbook خطای validation داشته باشد، Domain write نباید partial اجرا شود.

Apply جامع نیز داخل transaction انجام می‌شود.

هدف:

```text
all valid -> apply
any validation error -> no partial domain import
```

## 11. Upsert و Summary

Import جامع create/update انجام می‌دهد و قبل از apply snapshot می‌گیرد تا unchanged را تشخیص دهد.

Summary مهم:

```text
classes_created
classes_updated
classes_unchanged
students_created
students_updated
students_unchanged
enrollments_created
enrollments_updated
enrollments_unchanged
evaluations_created
evaluations_updated
evaluations_unchanged
metric_scores_created
metric_scores_updated
metric_scores_unchanged
```

Metadata:

```text
template_version = 1.0
source = comprehensive_school
records_deleted = 0
delete_policy = explicit_manual_only
```

## 12. چرا Missing Row حذف نیست؟

Excel یک snapshot ناقص/ویرایش‌پذیر کاربر است. حذف یک row ممکن است به دلیل:

- اشتباه کاربر
- filter/copy-paste
- ناقص بودن فایل
- نسخه قدیمی فایل
- حذف تصادفی Sheet row

باشد.

بنابراین:

```text
absence != delete intent
```

حذف باید explicit و auditable باشد.

## 13. Public Import API

### Create

```http
POST /api/v1/imports/
```

multipart fields:

```text
school
import_type
source_file
```

فقط:

```text
import_type=comprehensive_school
```

قواعد file:

```text
extension: .xlsx
max size: 10 MB
```

### List / Retrieve

```http
GET /api/v1/imports/
GET /api/v1/imports/{id}/
```

Queryset فقط Jobهایی را نشان می‌دهد که `school_id` آن‌ها داخل `selected_school_ids(request)` است.

### Retry

```http
POST /api/v1/imports/{id}/retry/
```

فقط failed یا processing stale.

### Cancel

```http
POST /api/v1/imports/{id}/cancel/
```

فقط queued/processing.

### Errors

```http
GET /api/v1/imports/{id}/errors/
```

خروجی XLSX با Sheet `errors` و `scope`.

## 14. Roleهای Import

Import جدید برای roleهای زیر تعریف شده است:

```text
system_admin
organization_admin
school_manager
educational_deputy
operator
```

Teacher public import نمی‌سازد.

## 15. Manual Entry Hub

Route:

```text
/manual-entry
```

هدف:

- کاهش سردرگمی فرم خام
- نمایش dependency order
- توضیح fieldهای مهم
- relation picker به جای UUID typing
- مسیر واضح برای create و manage

## 16. Field Hintهای مهم Manual UI

نمونه‌ها:

### national_id

```text
دقیقاً ۱۰ رقم؛ صفر ابتدایی را حذف نکنید
```

### student_number

```text
در همان مدرسه و سال تحصیلی یکتا باشد
```

### enrollment

```text
ثبت‌نام فعال را با دانش‌آموز/کلاس انتخاب کنید
```

### class_section

```text
با نام یا کد انتخاب شود؛ UUID تایپ نشود
```

### reason

```text
دلیل واقعی و قابل پیگیری برای Audit
```

## 17. Manual Monthly Evaluation — Catalog

```http
GET /api/v1/monthly-evaluations/catalog/
```

Response:

```json
{
  "framework_version": "1.0",
  "score_min": 0,
  "score_max": 5,
  "metric_count": 74,
  "metrics": []
}
```

هر item:

```json
{
  "code": "EDU_01",
  "title": "نمرات درسی",
  "domain_code": "EDU",
  "domain_title": "آموزشی",
  "domain_weight": 20,
  "order": 1
}
```

## 18. Manual Monthly Evaluation — Upsert

```http
POST /api/v1/monthly-evaluations/manual/
```

Request example:

```json
{
  "enrollment": "8e00646d-....",
  "month_no": 4,
  "note": "عملکرد مناسب",
  "metrics": [
    {"metric_code": "EDU_01", "value": 4},
    {"metric_code": "EDU_02", "value": 5}
  ]
}
```

Validation exact:

- enrollment: UUID
- month_no: integer 1..12
- note: optional/blank, max 5000
- metrics: optional list
- metric_code: Choice from Catalog
- value: integer 0..5
- duplicate metric code: rejected
- metrics empty + note blank: rejected

## 19. Enrollment Scope Manual Evaluation

Backend Enrollment را با این محدودیت‌ها resolve می‌کند:

```text
school_id in selected_school_ids(request)
class_section_id in allowed_class_ids(request.user, school_ids)
status = active
```

اگر UUID syntactically درست ولی خارج Scope باشد، write انجام نمی‌شود.

## 20. Upsert Behavior Manual Evaluation

Service با `select_for_update` evaluation matching را Lock می‌کند:

```text
enrollment
month_no
FRAMEWORK_VERSION
```

حالت‌ها:

### No row

Create.

### Active row

Update same row.

### Soft-deleted row

Restore همان row و ادامه update.

### Metric omitted

Preserve old value.

### Metric included same value

`metrics_unchanged += 1`

### Metric included different value

Update.

### Metric new

Create.

### Imported evaluation manually edited

`source_import_job` قبلی حفظ می‌شود.

## 21. Manual Delete

```http
DELETE /api/v1/monthly-evaluations/{id}/manual/?reason=ثبت%20اشتباه
```

Reason validation:

```text
min_length = 3
max_length = 1000
```

Behavior:

- scoped get_object
- transaction
- select_for_update
- soft-delete
- metric history preserved
- Audit event
- 204 response

## 22. Enrollment Update/Delete متفاوت است

Enrollment را نباید با semantics MonthlyEvaluation اشتباه گرفت.

برای Enrollment:

- generic destructive delete/update برای history transition مسیر درست نیست
- change class، transfer و change status باید Actionهای اختصاصی باشند
- historical enrollment باید قابل audit باقی بماند

## 23. Student Identity

Student identity در Database بر اساس `organization + national_id` و constraintهای موجود Domain مدیریت می‌شود؛ `local_code` فایل identity global نیست.

Frontend UUID را نمایش نمی‌دهد، ولی Database identity و Scope همچنان backend concern است.

## 24. Frontend Import UX

صفحه Import جدید:

```text
Frontend/src/pages/imports-simple.ts
```

Behavior:

- فقط Comprehensive workflow
- download official template
- school selection
- `.xlsx` و 10MB UX validation
- local preview برای سه Sheet/headers/74 metric columns
- server validation همچنان authoritative است
- async job polling
- history جامع
- summary created/updated/unchanged
- errors preview/download
- retry/cancel
- link به `/manual-entry`

Client-side preview جای Backend validation را نمی‌گیرد.

## 25. Frontend Manual Evaluation UX

```text
Frontend/src/pages/manual-entry.ts
```

Dialog:

1. catalog fetch
2. enrollment search
3. month selection
4. existing evaluation fetch
5. prefill metrics/note
6. partial save
7. result toast
8. optional soft-delete with reason

Blank Metric در فرم یعنی:

```text
not entered / leave unchanged
```

نه score zero و نه delete.

## 26. Testهای Critical

Regression coverage اضافه‌شده برای:

- public import type restriction
- strict national id
- evaluation national-id mismatch
- name mismatch
- class mismatch
- no implicit delete
- accurate unchanged summary
- manual evaluation create/update
- preserve omitted metric
- preserve import provenance
- duplicate metric rejection
- cross-school write rejection
- soft-delete + reason
- restore deleted evaluation
- OpenAPI schema exactness

## 27. قواعد تغییر آینده Template

اگر Template جامع تغییر کرد:

1. Template version باید versionable بماند.
2. Parser/header validation با آن همگام شود.
3. Metric catalog تغییر باید deterministic باشد.
4. Backward compatibility یا migration path مشخص شود.
5. OpenAPI/Frontend در صورت تغییر API regenerate شود.
6. Test round-trip فایل رسمی اضافه/به‌روزرسانی شود.
7. نبود row همچنان نباید به delete تبدیل شود مگر طراحی explicit جدید با audit/confirmation انجام شود.
