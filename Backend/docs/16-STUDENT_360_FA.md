# 16 — Student 360 v1 (Implemented)

## وضعیت پیاده‌سازی

F1 به route موجود `/students/:id` افزوده شده است، بدون ساخت model یا table با نام Student360. endpointهای جداگانهٔ summary، academics، attendance، evaluations، behavior، activities، risks، recommendations و reports از selectorهای scoped استفاده می‌کنند و tabهای Frontend به‌صورت lazy بارگیری می‌شوند. Counseling عمداً endpoint یا کلید payload در این composition ندارد.

## اصل معماری

Student 360 یک **read composition** است، نه model، table، queue یا سیستم موازی. route موجود Frontend `/students/:id` باید به همین تجربه تبدیل شود.

## API هدف

| Endpoint | داده | شرط دسترسی |
|---|---|---|
| `GET /students/{id}/360/summary/` | هویت و خلاصهٔ مجاز | Student در school/class scope درخواست |
| `GET /students/{id}/360/academics/` | نتایج تحصیلی | scope + role مجاز |
| `GET /students/{id}/360/attendance/` | خلاصه حضور | scope + role مجاز |
| `GET /students/{id}/360/evaluations/` | 74 indicator/evaluation مجاز | scope + role مجاز |
| `GET /students/{id}/360/reports/` | archiveهای قابل رؤیت | scope + report permission |

Behavior، Activity، Risk و Recommendation در phaseهای بعد endpoint مستقل و lazy دارند. Counseling عمداً در هیچ payload عمومی 360 نیست.

## Selector و query rule

`build_student_360_summary(...)` در `students/selectors.py` باید ابتدا visible Enrollment را از `selected_school_ids` و `allowed_class_ids` ثابت کند، سپس queryهای select/prefetch محدود را انجام دهد. serializer/view نباید دادهٔ unscoped را واکشی و بعد در Frontend مخفی کند.

## Frontend

tabها: Summary، Academic، Attendance، 74 Indicators، Behavior، Activities، Risk، Recommendations، Reports و Counseling فقط هنگام capability مجاز. هر tab lazy-load و از `src/api/` استفاده می‌کند؛ local response interfaceهای page جایگزین generated contract می‌شوند.

## تست الزامی

- allowed/denied role، cross-organization، cross-school و cross-class.
- عدم وجود کلید Counseling در JSON، حتی برای کاربر غیرمجاز.
- قرارداد OpenAPI و lazy-load UI برای هر section.
- query-count regression برای summary در دادهٔ نمونهٔ واقعی.
