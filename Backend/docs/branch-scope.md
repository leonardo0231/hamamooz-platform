# Fixed Besat Scope Policy

The deployment has one school only: Besat School. Every former school relation
is stored against the Besat child of the organization, and clients cannot
select or create another school.

Required:

- queryset scope
- object permission
- service validation
- async task validation
- export/report validation

The only client scope header is `X-Organization-ID`. The legacy
`X-School-ID` header is accepted server-side only as a consistency check for
old clients; it never changes the fixed Besat scope. Malformed or unrelated
identifiers are rejected.
