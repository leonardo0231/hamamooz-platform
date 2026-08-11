# واژه‌نامه و مرزهای دامنه‌ای

| اصطلاح | تعریف | مرز مجوز/تاریخچه |
|---|---|---|
| Organization | tenant سطح مجموعه | مرز اول isolation |
| School | شعبهٔ Organization | مرز عملیاتی اغلب endpointها |
| Student | هویت شخصی دانش‌آموز | در Organization یکتا با national ID |
| Enrollment | عضویت زمان‌مند دانش‌آموز در School/Year/Class | مرجع cohort و انتقال |
| Student 360 | composition فقط-خواندنی از domainهای مجاز | Counseling را شامل نمی‌شود |
| Evaluation Framework | catalog versioned 74 metric | snapshot framework version در MonthlyEvaluation |
| Behavior Event | واقعهٔ مثبت/منفی ثبت‌شده | state: draft→confirmed→under_follow_up→resolved؛ draft/confirmed→voided |
| Activity | رویداد فرهنگی/مسابقه/پژوهشی/ورزشی/هنری/other | مشارکت از خود فعالیت جداست |
| Counseling Case | پروندهٔ confidential | Private Note فقط Counselor؛ shared/released دادهٔ جداگانه |
| Referral | hand-off صریح برای انتقال دادهٔ حساس | انتقال School خودکار مجوز خواندن نیست |
| Guide Assignment | پیوند Guide Teacher به Enrollment با `starts_at`/`ends_at` | با انتقال/تغییر کلاس پایان‌پذیر |
| Risk Signal | خروجی Rule deterministic | `rule_code`, `rule_version`, severity, evidence, explanation, window |
| Operational Alert | اعلان عملیاتی بر پایهٔ signal | جایگزین signal نیست |
| Recommendation | پیشنهاد قابل بازبینی برای یک audience | record مستقل برای هر audience |
| Report Draft | پیش‌نویس قابل ویرایش کنترل‌شده | قبل از archive |
| Report Archive | خروجی رسمی immutable | snapshot و formula version ثابت |
| Portal Visibility Policy | تصمیم server-side دربارهٔ دادهٔ منتشرشدنی | counseling=never، report=released-only |

## Context map

```text
students (Student, Enrollment)
  ├─ evaluations (structured assessor opinion)
  ├─ attendance / academics (operational facts)
  ├─ behavior / activities (new facts and evidence)
  ├─ guidance (enrollment-based support)
  ├─ counseling (confidential boundary; separate)
  ├─ analytics (read + deterministic signals)
  ├─ recommendations (reviewed communication)
  └─ reports / dashboard / portal (read/output boundaries)
```

## نام‌گذاری API و مدل

- نام resourceها جمع و actionهای workflow صریح هستند؛ `preview`, `approve`, `resolve` و `void` generic CRUD تلقی نمی‌شوند.
- هر record تاریخی باید actor، timestamp و version مناسب داشته باشد؛ متن محرمانه به log یا audit snapshot منتقل نمی‌شود.
- client supplied ID فقط selector نیست؛ server رابطهٔ object با scope را بررسی می‌کند.
