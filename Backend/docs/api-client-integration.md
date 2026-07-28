# API Client Integration

## Authentication

1. Send email and password to `POST /api/v1/auth/login/`.
2. Keep the short-lived access token in memory where possible.
3. Send `Authorization: Bearer <access>` on protected requests.
4. Rotate the refresh token through `POST /api/v1/auth/refresh/`.
5. Send the current refresh token to `/auth/logout/` to blacklist it.

## Error envelope

```json
{
  "code": "machine_readable_code",
  "message": "Human-readable message",
  "details": {},
  "trace_id": "request-correlation-id"
}
```

An API client may send `X-Request-ID`; the backend returns the effective value in the same response header and error body.

## Pagination

List endpoints use `count`, `next`, `previous`, and `results`. `page_size` is capped at 100.

Clients must never treat hidden controls as authorization. The backend remains authoritative for every action and object.
