# ADR 0002: Email Login with Rotating JWT

- Status: accepted for MVP
- Decision: use a custom Django user from migration zero, unique email as login, short-lived access JWTs and rotating blacklisted refresh JWTs.
- Rationale: stable authentication for independent API clients without coupling to browser sessions.
- Consequence: refresh token storage and rotation behavior must be implemented carefully by each client; tokens are never logged.
