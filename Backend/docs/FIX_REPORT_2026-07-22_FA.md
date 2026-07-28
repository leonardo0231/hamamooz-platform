# گزارش اصلاحات یکپارچه ۱۴۰۵/۰۴/۳۱ (2026-07-22)

## ساختار و بسته‌بندی

- یکپارچه‌سازی appها زیر `hamamooz.apps` و حذف ساختار legacy `Backend/apps`.
- افزودن package discovery برای نصب editable.
- حذف cache، محیط مجازی، SQLite، coverage و schemaهای استاتیک stale از بسته.
- افزودن `.gitignore` و سخت‌گیری `.dockerignore`.

## گزارش و PDF

- بازگرداندن جدایی صحیح `render_report_html` و `render_report_pdf`.
- lazy-load کردن WeasyPrint فقط هنگام تولید PDF.
- confinement مسیر media برای جلوگیری از file traversal.
- claim/idempotency و timeout برای task گزارش و پاک‌سازی فایل orphan.
- roster تاریخ‌مند و کاهش queryهای تکراری محاسبه دسته‌های نمره.

## Attendance

- migration و استقرار canonical app.
- اصلاح Django Admin با `raw_id_fields`.
- roster بر اساس تاریخ عضویت، مخفی‌کردن session لغوشده و افزودن workflow cancel.
- revision/audit اتمیک برای ثبت، اصلاح و عذر.
- claim اتمیک اعلان، retry با backoff، dead-letter، stale recovery و جلوگیری از ارسال تکراری.
- عدم ثبت دروغین کانال in-app به‌عنوان sent.
- ماسک اطلاعات گیرنده در Console SMS.
- قفل و idempotency ارزیابی alert.
- افزودن تست‌های workflow اصلی attendance.

## تاریخچه تحصیلی و محاسبات

- تغییر کلاس با بستن Enrollment قبلی و ساخت Enrollment جدید از تاریخ مؤثر.
- اعمال roster تاریخ‌مند در گزارش و محاسبات.
- immutable کردن روابط ساختاری پس از ایجاد داده وابسته.
- هماهنگ‌سازی status دانش‌آموز با Enrollmentها.
- الزام کامل‌بودن نتایج پیش از قبولی و پاک‌کردن rankهای stale.
- جلوگیری از چند CalculationPolicy فعال برای یک scope با migration داده و constraint.
- جلوگیری از ترکیب ترم‌های مختلف در Dashboard.

## امنیت و Audit

- default-deny برای actionهای unsafe بدون mapping نقش.
- login با username یا email و audit موفق/ناموفق بدون ذخیره identifier خام.
- revoke کردن refresh tokenها در تغییر رمز و غیرفعال‌سازی کاربر.
- redaction بازگشتی PII در audit و parsing امن forwarded IP.
- اتمیک‌کردن mutation و audit.
- حفاظت soft-delete در برابر رابطه‌های `PROTECT` فعال و افزودن restore validation.

## Import، عملیات و استقرار

- محدودیت row/column/string/uncompressed size و compression ratio برای XLSX.
- batch preload برای حذف N+1 lookupهای import.
- recovery jobهای PROCESSING قدیمی و ثبت failureهای غیرمنتظره.
- PostgreSQL اجباری و secret/storage/email validation در production.
- اجرای container با user غیر root.
- جداکردن Redis cache از broker و استفاده از `noeviction` برای broker.
- انتقال migration/collectstatic به service یک‌بارمصرف `release`.
- پشتیبانی صحیح local media و profile اختیاری MinIO/S3.
- backup دیتابیس و object storage، readiness کامل‌تر و retention command.
- حذف Nginx config قدیمی و افزودن نمونه TLS مستقل.

## پیش‌نیازهای محیطی باقی‌مانده

این موارد bug سورس نیستند و باید در محیط مقصد فراهم شوند:

- Pango/GObject برای WeasyPrint روی Windows، یا اجرای Docker لینوکسی.
- PostgreSQL برای تست‌های locking/concurrency.
- credential واقعی SMTP/SMS/S3 در production.
- مقصد backup رمزگذاری‌شده و off-host.
