# API Changelog

تمام تغییرات مهم و ناسازگار API در این فایل ثبت می‌شوند.

## [Unreleased]

### Added

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

### Changed

- Import ارزیابی ماهانه اکنون هر دو قالب طولی نسخه ۱ و عریض هوشمند نسخه ۲ را می‌پذیرد.
- پاسخ ارزیابی ماهانه اطلاعات تکمیل و سطح عملکرد نهایی را به‌صورت صریح برمی‌گرداند.
- Repository از حالت Backend-only به ساختار Monorepo تغییر کرد.
- قرارداد OpenAPI مستقیماً از کد جاری Backend بازتولید شد.

### Deprecated

- هیچ موردی وجود ندارد.

### Removed

- هیچ موردی وجود ندارد.

### Fixed

- Security Requirement تکراری در عملیات‌های OpenAPI حذف شد.
- مقدار نهایی اعلان همگام قبل از Serialization از پایگاه داده بازخوانی می‌شود.

### Breaking Changes

- هیچ موردی وجود ندارد.

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
