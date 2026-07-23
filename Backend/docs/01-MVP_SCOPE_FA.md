# دامنه و وضعیت MVP

## هدف

هسته‌ای عملیاتی برای ۱۳ شعبه که ساختار آموزشی، کاربران و نقش‌ها، دانش‌آموز، ثبت‌نام تاریخ‌مند، درس، نمره، کارنامه، حضور و غیاب، Import و عملیات استقرار را با جداسازی امن شعب پوشش دهد.

## ماتریس تحویل

| نیاز MVP | وضعیت | محل پیاده‌سازی |
|---|---:|---|
| مجموعه، شعبه فعال/غیرفعال، سال، نوبت، پایه، کلاس و ظرفیت | کامل | `organizations` |
| ۶ نقش و نقش متفاوت در شعب مختلف | کامل | `accounts.RoleAssignment` |
| JWT، تغییر رمز، غیرفعال‌سازی، ورود/خروج و Audit | کامل | `accounts`, `core.AuditEvent` |
| پرونده دانش‌آموز، عکس، وضعیت و جست‌وجو | کامل | `students.Student` |
| ولی و ارتباط یک ولی با چند دانش‌آموز | کامل | `Guardian`, `StudentGuardian` |
| ثبت‌نام سالانه و سوابق تاریخ‌مند | کامل | `Enrollment`, `EnrollmentEvent` |
| تغییر کلاس و انتقال بین شعب با حفظ تاریخچه | کامل | Service layer دانش‌آموز |
| درس، درس پایه، ارائه در کلاس و تخصیص دبیر | کامل | `academics` |
| ارزیابی، سقف، وزن، تاریخ و ثبت گروهی | کامل | `Assessment`, bulk API |
| غیبت موجه/غیرموجه و نمره ثبت‌نشده | کامل | `Score.Status` |
| ارسال، رد، تأیید و قفل ارزیابی | کامل | Assessment workflow service |
| تاریخچه تغییر و اصلاح نمره قفل‌شده | کامل | `ScoreRevision` |
| معدل درس/نوبت، ضریب، وزن، گردکردن و قبولی | کامل | `calculations.py` |
| رتبه Dense کلاس | کامل | `recalculate_class_term` |
| نسخه فرمول برای مجموعه/سال/پایه | کامل | `CalculationPolicy` و Resultها |
| کارنامه فردی و گروهی A4 فارسی | کامل | `reports` + WeasyPrint |
| پیش‌نمایش و آرشیو Snapshot/PDF | کامل | `/reports/preview/`, `ReportArchive` |
| Import ثابت دانش‌آموز، ثبت‌نام و نمره | کامل | `imports` + قالب‌های XLSX |
| جلوگیری از ثبت ناقص Import و گزارش خطا | کامل | validate-all سپس transaction-all |
| حضور روزانه و زنگ | کامل | `attendance.AttendanceSession` |
| roster تاریخ‌مند، ثبت گروهی، finalize و cancel | کامل | Attendance service/API |
| توجیه غیبت، مدارک، تأیید/رد و revision | کامل | `AttendanceRecord`, `AbsenceEvidence` |
| هشدار غیبت و اعلان والدین | کامل با محدودیت کانال | `AttendanceAlert`, `ParentNotification` |
| داشبورد عملیاتی | کامل | `/dashboard/summary/` |
| PostgreSQL، Redis، Celery و FileSystem/S3 | کامل | Settings و Compose |
| OpenAPI نسخه‌دار و UI مستندات | کامل پویا | `/api/v1/schema/`, Swagger/ReDoc |
| Log، Audit، Health و Sentry اختیاری | کامل | `core` و Settings |
| بکاپ DB، رسانه و S3 و Restore | کامل در سطح Host | Compose و اسکریپت‌ها |
| Development/Test/Production settings | کامل | `config/settings/` |

## معیارهای پذیرش

- `seed_demo` دقیقاً ۱۳ شعبه و داده پایه را به‌شکل idempotent ایجاد می‌کند.
- Queryهای لیست صفحه‌بندی شده و Scope شعبه/کلاس/درس قبل از Serialize اعمال می‌شود.
- دبیر فقط CourseOfferingهای خودش و کلاس‌های مرتبط را می‌بیند.
- نوشتن برای کاربر غیرسیستمی بدون `X-School-ID` یا `X-Organization-ID` صریح رد می‌شود.
- تغییر کلاس و انتقال، Enrollment قبلی را بازنویسی نمی‌کنند و رویداد تاریخ‌مند می‌سازند.
- قفل ارزیابی فقط پس از تکمیل roster نمرات انجام می‌شود.
- محاسبات از `Decimal` و Policy نسخه‌دار استفاده می‌کنند.
- Import با یک ردیف خطا هیچ Write دامنه‌ای Commit نمی‌کند.
- Attendance فقط بر اساس Enrollment معتبر در تاریخ جلسه roster می‌سازد.
- گزارش رسمی Snapshot و نسخه فرمول را همراه فایل نگه می‌دارد.

## محدودیت‌های آگاهانه MVP

- رابط کاربری در این شاخه نیست.
- پنل مستقل والد/دانش‌آموز وجود ندارد؛ کانال `in_app` به‌عنوان ارسال موفق ثبت نمی‌شود.
- ارسال SMS پیش‌فرض غیرفعال است و به Backend واقعی نیاز دارد.
- گزارش‌ساز قابل طراحی، Word/A3 و تحلیل مقایسه‌ای پیشرفته شعب پیاده‌سازی نشده‌اند.
- رفتار و انضباط، فعالیت فرهنگی، مهارت نرم، مشاوره و تحلیل چندساله خارج از دامنه‌اند.
- 2FA، مدیریت دستگاه/نشست، WAF، Antivirus فایل، PITR و Audit کامل Readها خارج از MVP هستند.
- Load test نهایی باید روی سخت‌افزار مقصد و داده نزدیک Production انجام شود.
