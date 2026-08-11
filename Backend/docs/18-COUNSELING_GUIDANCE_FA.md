# 18 — Counseling و Guidance (Implemented, Security-Critical)

## وضعیت پیاده‌سازی

F3 با appهای جداگانهٔ `counseling` و `guidance` پیاده‌سازی شده است. Private session/note فقط با assignment مستقیم Counselor قابل مشاهده است؛ system admin و manager bypass پیش‌فرض ندارند. referral فقط hand-off صریحِ بدون کپی session ایجاد می‌کند و انتقال enrollment به‌تنهایی دادهٔ محرمانه را منتقل نمی‌کند. break-glass عمداً در این نسخه فعال نشده است؛ رفتار پیش‌فرض deny است تا policy محصول برای آن تصویب شود.

## Counseling confidentiality boundary

مدل‌ها: `CounselingCase`, `CounselingSession`, `CounselingFollowUp`, `Referral`, `CounselingActionPlan`, `CounselingAttachment`.

| لایه | مخاطب مجاز | دادهٔ ممنوع |
|---|---|---|
| Private Note | Counselor دارای case scope | همه نقش‌های دیگر، حتی system admin پیش‌فرض |
| Shared risk/follow-up | Counselor و نقش‌های محدود طبق policy | متن جلسه/یادداشت خصوصی |
| Released guidance | teacher/parent/student طبق انتشار | دادهٔ confidential |

Audit confidential read فقط `actor`, `case/session ID`, `timestamp`, `reason`, `request ID`, `scope` را ثبت می‌کند. متن جلسه/یادداشت در log یا metadata ذخیره نمی‌شود.

## Threat model

| تهدید | کنترل لازم | تست اثبات |
|---|---|---|
| manager/admin همهٔ noteها را بخواند | default-deny permission و selector جدا | role denial API test |
| cross-school case leak | school/case scope و referral صریح | target-school denial test |
| transfer data disclosure | hand-off policy جدا از Enrollment transfer | referral-only visibility test |
| break-glass سوءاستفاده | privilege + reason + audit + time-bound policy | missing reason/privilege denial |
| PII در log | structured redaction و metadata allowlist | log/audit inspection test |

## Guidance

`GuideTeacherAssignment(guide_teacher, enrollment, starts_at, ends_at)` مبنای cohort است. `GuideFollowUp` و `GuideActionPlan` به assignment/enrollment مرتبط‌اند؛ assignment دائمی به Student ساخته نمی‌شود.

## Migration/API gate

roleهای `COUNSELOR`, `GUIDE_TEACHER`, `STUDENT_AFFAIRS_DEPUTY` additive اضافه می‌شوند. API Counseling جدا از 360 و portal است. قبل از production، retention، disclosure، break-glass و transfer policy باید توسط مالک محصول تأیید و در security review ثبت شود.
