# 17 — Behavior و Activities (Implemented)

## وضعیت پیاده‌سازی

F2 در دو app مستقل `behavior` و `activities` پیاده‌سازی شده است. migrationها، constraintها، serviceهای transition/revision، APIهای scoped و تست‌های state/audit/cross-school موجودند. نقش `STUDENT_AFFAIRS_DEPUTY` فقط در scopeهای صریح این domainها whole-school access دارد و به broad scope آموزشی عمومی تبدیل نشده است.

## Behavior bounded context

مدل‌ها: `BehaviorEventType`, `BehaviorEvent`, `BehaviorAction`, `BehaviorFollowUp`, `BehaviorAttachment`.

`BehaviorEvent` حداقل مالکیت `organization`, `school`, `academic_year`, `enrollment`, `event_type`, `polarity`, `severity`, `occurred_at`, `description`, `status`, `recorded_by`, `confirmed_by`, `confirmed_at` دارد.

```text
draft -> confirmed -> under_follow_up -> resolved
draft -------------------------------> voided
confirmed ---------------------------> voided
```

- بعد از `confirmed` اصلاح حساس revision/audit لازم دارد.
- Event evidence است و **نباید** `DIS_03` یا metric Monthly Evaluation را خودکار تغییر دهد.
- attachment باید storage authorization و content/size validation داشته باشد.

## Activities bounded context

مدل‌ها: `Activity`, `ActivityParticipation`, `ActivityAchievement`, `ActivityAttachment`.

`Activity.kind` فقط `cultural`, `competition`, `research`, `sport`, `art`, `other` است. Participation به `activity` و `enrollment` وصل می‌شود و `status`, `participation_role`, `result`, `placement`, `notes` را نگه می‌دارد.

## قواعد database و migration

1. FKهای historical با `PROTECT`؛ `organization/school/enrollment` در یک transaction validate شوند.
2. indexها حداقل برای `(school, academic_year, status, occurred_at)` و queryهای enrollment-based بر اساس evidence query تعیین شوند.
3. constraintهای enum/state، uniqueness موردنیاز و ordering migration-safe تعریف شوند.
4. migration ابتدا additive، سپس data backfill idempotent، سپس validation/constraint جداگانه باشد؛ downgrade path و backup/restore test ثبت شود.

## API و تست

resourceهای pagination/filter/sort‌شده باید validation، 403/404 non-disclosure policy، cross-scope و transition test داشته باشند. Workflow حساس باید PostgreSQL واقعی برای double-confirm، void race و duplicate attachment بررسی شود.
