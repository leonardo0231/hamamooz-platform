# Branch Scope Policy

Every school-scoped resource must be filtered from the authenticated user's active memberships.

Forbidden:

- filtering only in serializer
- trusting frontend school_id
- checking only role name


Required:

- queryset scope
- object permission
- service validation
- async task validation
- export/report validation