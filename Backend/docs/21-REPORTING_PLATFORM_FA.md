# 21 — Reporting Platform (Implemented Extension)

## وضعیت پیاده‌سازی

F6 `ReportTemplate` و `ReportDraft` را با workflow draft → submit → approve → render → archive پیاده‌سازی می‌کند. template فقط blockهای allowlisted و overrideهای متنی کنترل‌شده می‌پذیرد. PDF رسمی از مسیر Chromium/Playwright و Word editable با `docxtpl` و template کنترل‌شدهٔ `templates/reports/report_card.docx` ساخته می‌شود؛ در نبود browser bundle خطای صریح ثبت می‌شود و fallback پنهان وجود ندارد. archive و MIME دانلود format خروجی را ثبت می‌کنند. Snapshot recommendation محرمانهٔ Counselor را شامل نمی‌شود.

## وضع فعلی

`ReportArchive` فعلی snapshot و `formula_version` دارد و خروجی رسمی immutable است. این رفتار حفظ می‌شود.

## مدل و workflow هدف

مدل‌های جدید: `ReportTemplate`, `ReportDraft`.

```text
Create Draft -> Build Snapshot -> Preview -> Human Edit -> Submit -> Approve -> Render -> Archive
```

Snapshot رسمی شامل student، grades، calculation policy/version، attendance، evaluation framework/version، behavior/activity evidence استفاده‌شده، analytics rule/signal، recommendation version و approved text است.

## Template policy

تنها blockهای allowlisted قابل تنظیم‌اند:

```json
{"blocks": ["student_identity", "academic_summary", "attendance_summary", "evaluation_radar", "strengths", "weaknesses", "recommendations", "signatures"]}
```

مدیر فقط ترتیب، نمایش، title، logo، signature، footer و style محدود را تنظیم می‌کند. اجرای Jinja/Python سفارشی ممنوع است.

## Format و تست

Chromium/Playwright برای PDF و `docxtpl` برای Word editable پیاده‌سازی شده‌اند. `presentation.page_size` فقط مقدارهای allowlisted `a4_portrait` و `a3_landscape` می‌پذیرد؛ بنابراین A3 landscape با renderer مرورگر و بدون CSS/Jinja دلخواه ساخته می‌شود. وابستگی renderer قدیمی از سطح runtime حذف شده است. Test ثابت می‌کند snapshot پس از تغییر دادهٔ جاری همان semantic result را بازتولید می‌کند.
