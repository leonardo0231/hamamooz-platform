# ADR 0017: Student 360 Is a Read Composition

- Status: accepted
- Date: 2026-08-10

## Context

The frontend already has a student route and source domains own academics, attendance, evaluations and reports. A persistence model named `Student360` would duplicate history and introduce synchronization/security risks.

## Decision

Extend `/students/:id` with scoped selector-backed, lazy endpoints for summary, academics, attendance, evaluations and reports. Do not create a `Student360` database model or include Counseling in a general 360 response.

## Consequences

- Each section has an explicit permission boundary and failure mode.
- Frontend latency improves through lazy loading.
- New composition fields require selector, query-count, authorization and OpenAPI review.

## References

- `Backend/docs/16-STUDENT_360_FA.md`
- `docs/product/FULL_PRODUCT_ROADMAP_FA.md`
