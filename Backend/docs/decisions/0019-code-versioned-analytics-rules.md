# ADR 0019: Analytics Rules Are Code-Versioned

- Status: accepted
- Date: 2026-08-10

## Context

Risk signals affect follow-up decisions and must be reproducible. A general purpose rule builder/DSL increases attack surface, version ambiguity and test burden.

## Decision

Store algorithms as reviewed Python rule classes with explicit code and version. Allow `AnalyticsRuleConfig` to control scoped parameters and activation dates only. Persist rule code/version, severity, evidence, explanation and window on every signal.

## Consequences

- Golden fixtures can assert exact output.
- Rule behavior changes require code review and a new version.
- Analytics uses targeted `on_commit` work plus daily reconciliation, not a new event bus.

## References

- `Backend/docs/19-ANALYTICS_RISK_FA.md`
- `spec/spec-architecture-full-product-v1.md`
