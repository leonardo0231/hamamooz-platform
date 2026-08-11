# ADR 0018: Counseling Has a Confidentiality Boundary

- Status: accepted
- Date: 2026-08-10

## Context

Counseling notes are more sensitive than ordinary school operational data. A broad manager/system-admin role or frontend-only hiding would allow data leakage.

## Decision

Implement Counseling as a separate domain with private, shared and released representations. Default access to Private Note is Counselor case scope only. School transfer does not grant access; explicit referral/handoff is required. Confidential read audit stores metadata but never session/note content.

## Consequences

- Counseling endpoints and selectors require dedicated permission tests.
- Break-glass, if later added, needs explicit privilege, reason and audit policy.
- Retention/disclosure policy is a production dependency rather than an implicit CRUD option.

## References

- `Backend/docs/18-COUNSELING_GUIDANCE_FA.md`
- `docs/product/REQUIREMENTS_TRACEABILITY_FA.md`
