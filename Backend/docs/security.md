# Security Baseline

- JWT access tokens are short-lived and refresh tokens rotate and are blacklisted.
- Passwords use Django's configured validators and hashers.
- CORS origins are explicit environment settings; wildcard origins are not enabled.
- Trace logging excludes credentials and token bodies by policy.
- Production refuses the development secret and enables HSTS/proxy security settings.
- Object storage is private and uses signed access in report slices.
- Rate limiting is enabled at the DRF baseline and will be specialized per sensitive endpoint.
- Authorization is applied before query evaluation and again in business services for sensitive workflows.
- No real secrets are committed; `.env.example` contains placeholders only.
