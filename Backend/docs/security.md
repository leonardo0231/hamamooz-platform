# Security Baseline

- JWT access tokens are short-lived and refresh tokens rotate and are blacklisted.
- Passwords use Django's configured validators and hashers.
- CORS origins are explicit environment settings; wildcard origins are not enabled.
- Trace logging excludes credentials and token bodies by policy.
- Production refuses short/placeholder application, database and object-storage secrets,
  requires explicit allowed hosts, and enables HSTS/proxy security settings.
- Object storage is private and uses signed access in report slices.
- The bundled MinIO bucket enables object versioning and its administrative console is bound to
  loopback only.
- Rate limiting is enabled at the DRF baseline and will be specialized per sensitive endpoint.
- Authorization is applied before query evaluation and again in business services for sensitive workflows.
- Non-system write requests must carry `X-School-ID` or `X-Organization-ID`; the requested scope is
  checked both before and after persistence and cross-branch writes are rolled back.
- `X-Forwarded-For` is ignored unless `TRUST_X_FORWARDED_FOR=true`; enable it only when the app can
  receive traffic exclusively through a trusted reverse proxy.
- No real secrets are committed; `.env.example` contains placeholders only.
