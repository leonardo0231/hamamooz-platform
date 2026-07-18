# Branch Scope Policy

Every school-scoped resource must be filtered from the authenticated user's active memberships.

Forbidden:

- filtering only in serializer
- trusting a client-provided school_id
- checking only role name


Required:

- queryset scope
- object permission
- service validation
- async task validation
- export/report validation

For unsafe API methods, non-system administrators must send an explicit `X-School-ID` or
`X-Organization-ID` header. A school header also derives and validates its organization; conflicting
headers and malformed UUIDs are rejected. Transfers require write authority in both source and
destination scope.
