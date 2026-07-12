# ADR 0002: Email Login with Rotating JWT

- Status: accepted for MVP
- Decision: use a custom Django user from migration zero, unique email as login, short-lived access JWTs and rotating blacklisted refresh JWTs.
- Rationale: stable API authentication for a separate frontend without coupling to browser sessions.
- Consequence: refresh token storage and rotation behavior must be implemented carefully by the frontend; tokens are never logged.
