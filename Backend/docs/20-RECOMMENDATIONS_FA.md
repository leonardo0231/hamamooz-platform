# 20 — Recommendation Engine (Implemented)

## وضعیت پیاده‌سازی

F5 workflow review/approval را با record مستقل برای هر audience پیاده‌سازی می‌کند. visibility در Backend اعمال می‌شود: recommendation مخاطب Counselor فقط برای Counselor دارای case scope قابل مشاهده یا transition است و حتی manager، system admin، Student 360 عمومی و snapshot گزارش رسمی آن را دریافت نمی‌کنند. AI همچنان خارج از تصمیم‌گیری رسمی است.

## Pipeline

```text
Signal -> rule -> Recommendation Draft -> Human Review -> Approved -> Visible/Reported
```

مدل‌ها: `Recommendation`, `RecommendationDecision`. Record هر audience مستقل است تا وضعیت Parent، Teacher و Counselor یکدیگر را تغییر ندهند.

فیلدهای اصلی: `student/enrollment`, `audience`, `rule_code`, `rule_version`, `priority`, `reason_snapshot`, `generated_text`, `approved_text`, `status`, `reviewer`, `approved_at`.

State machine:

```text
draft -> pending_review -> approved | rejected
approved -> dismissed | expired | superseded
```

## Policy

- تنها `approved_text` مطابق audience/visibility منتشر می‌شود.
- duplicate generation و double-approve با lock/constraint/service transition کنترل می‌شود.
- AI در آینده فقط rewrite اختیاریِ structured recommendation است؛ risk یا official recommendation را بدون deterministic evidence و human approval ایجاد نمی‌کند.

## تست

هر transition، reviewer scope، audience isolation، duplicate operation، expired/superseded و report/portal visibility باید PostgreSQL/API test داشته باشد.
