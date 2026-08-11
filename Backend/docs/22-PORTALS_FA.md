# 22 — Parent و Student Portal (Implemented)

## وضعیت پیاده‌سازی

F7 با `GuardianAccount` و `StudentAccount` و endpointهای `/portal/*` پیاده‌سازی شده است. انتخاب child در server از relationship معتبر استخراج می‌شود، نه ID ارسالی client. `PortalVisibilityPolicy` فقط report released، recommendation approved برای audience، attendance و plan released را منتشر می‌کند و policy Counseling به‌صورت سخت‌گیرانه فقط `never` است.

## مدل authorization

Parent/Student Staff Role عادی نیستند.

```text
Parent: User -> GuardianAccount -> Guardian -> StudentGuardian -> Student
Student: User -> StudentAccount -> Student
```

API هرگز `student_id` ارسالی client را trusted scope نمی‌داند. ابتدا server فهرست relationshipهای معتبر را می‌سازد، سپس object را در همان فهرست select می‌کند.

## Visibility policy هدف

| داده | Parent/Student portal |
|---|---|
| report card | فقط released |
| recommendation | فقط approved برای audience |
| attendance summary | طبق policy visible |
| behavior | hidden در v1 |
| counseling | never |
| guide plan | فقط released |

## قابلیت‌ها

Parent: my children، switch child، released reports، approved recommendations، follow-up plans، notification acknowledgement، consent/privacy.

Student: my reports، progress، approved recommendations و released follow-up plan.

## تست امنیتی الزامی

Guardian→Student relationship، child switch، supplied cross-student ID، cross-school access، parent/student visibility، private Counseling absence، released-only report و approved-only recommendation. پاسخ 403/404 باید با non-disclosure policy موجود یکسان باشد.
