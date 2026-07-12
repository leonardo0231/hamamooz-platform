# Assumptions and Resolved Ambiguities

1. The repository was empty at bootstrap, so no existing backend, migrations, dependencies, workflows or frontend files existed to preserve.
2. Email is the canonical login identifier. This is reversible only through a deliberate migration and API compatibility plan.
3. Internal primary keys use `BigAutoField`; UUID is not adopted globally without aggregate-specific justification.
4. Tehran is the business timezone while persisted datetimes remain timezone-aware UTC.
5. MVP exposes backend APIs, admin and API documentation only; no temporary React/Next.js frontend is created.
6. Attendance, behavior, counseling, advanced analytics, Word and A3 remain disabled until their designated versions.
7. A PostgreSQL/Redis Docker execution could not be performed in environments without Docker; CI is the authoritative infrastructure execution path until a local Docker run is recorded.
