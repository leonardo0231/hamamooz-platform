# 19 — Analytics و Risk Engine (Implemented)

## وضعیت پیاده‌سازی

F4 شامل ruleهای Python versioned، `AnalyticsRuleConfig`، `AnalyticsRun`، `StudentRiskSignal` و `OperationalAlert` است. mutationهای مرتبط task هدفمند را پس از commit زمان‌بندی می‌کنند و Celery Beat reconciliation روزانه را انجام می‌دهد. API evidence، explanation، window، rule code و version را بازمی‌گرداند؛ score مبهم بدون دلیل منتشر نمی‌شود.

## ساختار

```text
analytics/
  rules/{academic_drop,multi_subject_drop,attendance_risk,discipline_repeat,performance_volatility}.py
  models.py engine.py selectors.py services.py tasks.py tests/
```

مدل‌ها: `AnalyticsRuleConfig`, `AnalyticsRun`, `StudentRiskSignal`, `OperationalAlert`.

هر signal شامل `rule_code`, `rule_version`, `severity`, `evidence`, `explanation`, `window` است. Algorithm در Python code versioned می‌ماند؛ config فقط `enabled`, `parameters`, `effective_from`, `effective_to` را کنترل می‌کند.

## Ruleهای v1

`academic_drop_v1`, `multi_subject_drop_v1`, `high_unexcused_absence_v1`, `discipline_repeat_v1`, `performance_volatility_v1`, `peer_performance_drop_v1`, `missing_teacher_scores_v1`.

سه‌سال، moving average، volatility و peer comparison باید cohort دقیق `grade/class/subject` و window ثبت‌شده داشته باشند. API فقط score مبهم مانند `risk=82` بدون evidence برنمی‌گرداند.

## اجرا و integrity

- mutation موفق → `transaction.on_commit` → task محدود به student/scope متاثر.
- Celery Beat روزانه → reconciliation idempotent برای mismatch/missing run.
- unique/idempotency strategy مانع duplicate signal/run در retry و concurrency می‌شود.

Golden test برای هر fixture باید signal exact شامل version/evidence را اثبات کند. قبل از index جدید، query plan و production-like data اندازه‌گیری می‌شود.
