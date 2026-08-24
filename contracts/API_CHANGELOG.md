# API Changelog

تمام تغییرات مهم و ناسازگار API در این فایل ثبت می‌شوند.

## [Unreleased]

### Added

- `GET/POST /api/v1/academic-report-settings/` و `PATCH /api/v1/academic-report-settings/{id}/` برای وزن اعشاری نوبت‌ها، سه کلید مستقل نمایش رتبه و تاریخچه تغییر سیاست در سطح مدرسه/سال.
- `GET /api/v1/annual-results/` و `POST /api/v1/annual-results/recalculate/` برای نتایج سالانه وزنی، رتبه dense کلاس/پایه/مدرسه و جمعیت هر cohort.
- منابع مستقل تابستان در `/api/v1/summer-programs/`، `/summer-courses/`، `/summer-registrations/`، `/summer-course-registrations/`، `/summer-exams/` و `/summer-subject-scores/`؛ نهایی‌سازی آزمون از `POST /api/v1/summer-exams/{id}/finalize/` انجام می‌شود.
- هفت `layout_key` مستقل کارنامه در گزارش‌ها: `analytical_term_1`، `analytical_term_2`، `analytical_annual`، `final_term_1`، `final_term_2`، `final_annual` و `summer_report`.
- فیلدهای مشتق‌شده بازه، fingerprint منبع، شماره رهگیری و نسخه برای گردش پیش‌نویس/تأیید انسانی/صدور بایگانی‌شده.
- نوع Import جدید `comprehensive_school` برای ورود اتمیک کلاس‌ها، دانش‌آموزان، ثبت‌نام‌ها و ارزیابی‌های ۷۴ شاخصی از یک فایل XLSX
- فیلد `result_summary` در پاسخ Import و خطاهای مکان‌دار شامل شیت، ردیف، ستون و کد پایدار خطا
- قالب هوشمند نسخه ۲ ارزیابی ماهانه با متادیتای پایدار مدرسه، کلاس، ثبت‌نام و شاخص‌ها
- Endpointهای تحلیل دانش‌آموز، داشبورد کلاس/مدرسه و خروجی Excel ارزیابی‌های ماهانه
- وضعیت `provisional`/`final`، روند، نقاط قوت و ضعف، پیشنهاد و رتبه با تعداد واقعی افراد
- قرارداد رسمی OpenAPI در مسیر `contracts/openapi.yaml`
- مستندات اتصال Frontend و Backend
- استاندارد مدیریت تغییرات API
- Schema صریح پاسخ گزارش‌های حضور و غیاب دانش‌آموز، کلاس و شعبه
- Schema صریح درخواست و پاسخ اعلان خلاصه حضور و غیاب به اولیا
- `GET /api/v1/monthly-evaluations/catalog/` برای دریافت نسخه چارچوب و فهرست رسمی ۷۴ شاخص ارزیابی دستی
- `POST /api/v1/monthly-evaluations/manual/` برای ایجاد یا به‌روزرسانی امن و تدریجی ارزیابی ماهانه
- `DELETE /api/v1/monthly-evaluations/{id}/manual/` برای حذف منطقی ارزیابی ماهانه با دلیل و ثبت Audit

### Changed

- نوبت گزارش برای کارنامه‌های سالانه و تابستانی nullable است؛ مسیرهای قدیمی نوبت اول/دوم همچنان سازگار باقی می‌مانند و پورتال خانواده از `period_label` امن استفاده می‌کند.
- متن‌های قابل جایگزینی گزارش به فیلدهای توضیحی مجاز محدود شده‌اند و شناسه، هویت، نمره، معدل، رتبه و سیاست‌های آموزشی از مسیر گزارش قابل تغییر نیستند.
- ورود گروهی جدید از API عمومی فقط با `import_type=comprehensive_school` و فایل رسمی XLSX انجام می‌شود؛ انواع قدیمی فقط برای سابقه Jobهای قبلی حفظ شده‌اند.
- Endpoint قالب Import عمومی فقط `comprehensive_school` را ارائه می‌کند.
- اعتبارسنجی فایل جامع کد ملی را دقیقاً ۱۰ رقم بررسی می‌کند و دیگر مقدار کوتاه را با صفرگذاری خودکار اصلاح نمی‌کند.
- هویت قابل مشاهده در شیت ارزیابی شامل کد ملی، نام و کد کلاس با شیت دانش‌آموزان تطبیق داده می‌شود.
- `result_summary` فایل جامع اکنون تعداد `created`، `updated` و `unchanged` را برای کلاس، دانش‌آموز، ثبت‌نام، ارزیابی و شاخص‌ها تفکیک می‌کند و سیاست حذف را صریح گزارش می‌دهد.
- نبودن یک رکورد در فایل جامع به معنی حذف نیست؛ حذف فقط از مسیر دستی و صریح انجام می‌شود.
- ویرایش دستی ارزیابی ماهانه شاخص‌های ارسال‌نشده و `source_import_job` اولیه را حفظ می‌کند.
- Import ارزیابی ماهانه تاریخی همچنان هر دو قالب طولی نسخه ۱ و عریض هوشمند نسخه ۲ را برای Jobهای موجود می‌شناسد.
- پاسخ ارزیابی ماهانه اطلاعات تکمیل و سطح عملکرد نهایی را به‌صورت صریح برمی‌گرداند.
- Repository از حالت Backend-only به ساختار Monorepo تغییر کرد.
- قرارداد OpenAPI مستقیماً از کد جاری Backend بازتولید شد.

### Deprecated

- ایجاد Import جدید با انواع `students`، `enrollments`، `scores` و `monthly_evaluations` از API عمومی منسوخ شده و دیگر پذیرفته نمی‌شود.

### Removed

- Templateهای قدیمی Import از Endpoint عمومی دانلود قالب حذف شدند؛ Jobهای تاریخی و داده‌های قبلی حذف نشده‌اند.

### Fixed

- Security Requirement تکراری در عملیات‌های OpenAPI حذف شد.
- مقدار نهایی اعلان همگام قبل از Serialization از پایگاه داده بازخوانی می‌شود.
- مسیرهای ورود دستی ارزیابی ماهانه اکنون در OpenAPI و catalog تولیدشده Frontend ثبت شده‌اند و Frontend از registry مرکزی endpointها استفاده می‌کند.

### Breaking Changes

- کلاینت‌هایی که Import جدید را با `students`، `enrollments`، `scores` یا `monthly_evaluations` ایجاد می‌کردند باید به فایل جامع `comprehensive_school` مهاجرت کنند یا برای ثبت تکی از Endpointهای دامنه/پنل دستی استفاده کنند. Jobهای تاریخی قابل مشاهده و retry باقی می‌مانند.

---

## [1.0.0] - 2026-07-23

### Added

- Authentication API
- Organization and school API
- Student and enrollment API
- Academic and assessment API
- Attendance API
- Report API
- Import API
- Dashboard API
