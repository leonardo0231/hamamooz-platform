# API Changelog

تمام تغییرات مهم و ناسازگار API در این فایل ثبت می‌شوند.

## [Unreleased]

### Added

- قرارداد رسمی OpenAPI در مسیر `contracts/openapi.yaml`
- مستندات اتصال Frontend و Backend
- استاندارد مدیریت تغییرات API
- Schema صریح پاسخ گزارش‌های حضور و غیاب دانش‌آموز، کلاس و شعبه
- Schema صریح درخواست و پاسخ اعلان خلاصه حضور و غیاب به اولیا

### Changed

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
