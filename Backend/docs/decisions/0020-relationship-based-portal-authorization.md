# ADR 0020: Portal Authorization Is Relationship-Based

- Status: accepted
- Date: 2026-08-10

## Context

Parent and Student accounts are not staff scopes. A role check combined with a client-provided student identifier creates an IDOR path.

## Decision

Derive accessible students server-side from persisted GuardianAccount/Guardian/StudentGuardian/Student or StudentAccount/Student relationships. Apply PortalVisibilityPolicy after relationship scope, never before it.

## Consequences

- Every portal endpoint ignores untrusted scope assertions from the client.
- Cross-student/cross-school and released-only tests are release blockers.
- Counseling is permanently absent from portal visibility.

## References

- `Backend/docs/22-PORTALS_FA.md`
- `docs/product/DOMAIN_GLOSSARY_FA.md`
