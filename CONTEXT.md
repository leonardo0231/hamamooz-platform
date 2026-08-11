# HamAmoz Domain Context

این واژه‌نامهٔ کوتاه، مرزهای دامنه‌ای تثبیت‌شده برای توسعهٔ محصول کامل را مشخص می‌کند. این فایل فقط زبان مشترک را نگه می‌دارد؛ جزئیات API و پیاده‌سازی در [docs/product](docs/product/README.md) است.

| اصطلاح | تعریف |
|---|---|
| Organization | مجموعهٔ آموزشیِ مرز اول tenant isolation. |
| School | شعبه‌ای از یک Organization؛ محل وقوع داده‌های عملیاتی. |
| Student | هویت دانش‌آموز در سطح Organization؛ تاریخچهٔ تحصیل روی Enrollment است. |
| Enrollment | عضویت تاریخی Student در School، سال تحصیلی، پایه و کلاس. |
| Student 360 | نمای یکپارچه و فقط‌خواندنی از داده‌های مجاز دانش‌آموز؛ هویت مستقل نیست. |
| Monthly Evaluation | ارزیابی ساختاریافتهٔ ماهانه با framework و metric version ثابت. |
| Behavior Event | واقعیت رخ‌دادهٔ رفتاری با چرخهٔ پیگیری؛ جایگزین Monthly Evaluation نیست. |
| Activity | فعالیت/مسابقه و مشارکت دانش‌آموز؛ واقعیت رخ‌داده، نه امتیازدهی شاخص. |
| Counseling Case | پروندهٔ محرمانهٔ مشاوره با مرز دسترسی مستقل. |
| Guide Assignment | تخصیص زمان‌دار معلم راهنما به Enrollment، نه اتصال دائمی به Student. |
| Risk Signal | نتیجهٔ قانون تحلیلی، همراه دلیل و شواهد قابل بازبینی. |
| Recommendation | متن/اقدام پیشنهادی برای یک مخاطب که پس از بازبینی قابل انتشار است. |
| Report Archive | خروجی رسمی تغییرناپذیر همراه با وضعیت زمان صدور. |
| Guardian Relationship | رابطهٔ معتبر Guardian با Student؛ مبنای دسترسی والد. |

## Invariants

- Enrollment مرجع تاریخچه و cohort است؛ Student به‌تنهایی تاریخ تحصیل را بیان نمی‌کند.
- Behavior/Activity واقعیت رخ‌داده‌اند؛ Monthly Evaluation نظر ساختاریافته است.
- Private Counseling Note از guidance یا اطلاعات منتشرشدهٔ دانش‌آموزی متفاوت است.
- Report Archive معنای رسمی زمان صدور را نگه می‌دارد، نه صرفاً آخرین دادهٔ جاری را.
- Risk Signal و Recommendation دو مفهوم متفاوت‌اند: اول evidence تحلیلی است و دوم ارتباط/اقدام بازبینی‌شده.
