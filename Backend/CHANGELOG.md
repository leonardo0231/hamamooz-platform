# Changelog

All notable backend changes are documented here.

## [Unreleased]

### Added

- Slice 0 Django modular-monolith foundation.
- Custom email-based user model from the first migration.
- JWT login, refresh, verify, logout, current-user and password-change endpoints.
- PostgreSQL, Redis, Celery and optional S3-compatible storage configuration.
- Health and readiness endpoints with trace IDs.
- OpenAPI schema, Swagger UI and ReDoc.
- Docker stack and backend-only GitHub Actions workflow.
- Initial MVP requirements, ERD, permission matrix, API inventory and backlog documentation.
## 2026-07-22 - Backend consolidation and hardening

- Consolidated Django apps under `hamamooz.apps` and removed the legacy tree.
- Added and hardened attendance, notification, alert and historical roster workflows.
- Restored report HTML/PDF rendering and added processing idempotency.
- Preserved enrollment history for class changes and transfers.
- Added fail-closed permissions, audit redaction and JWT refresh revocation.
- Hardened imports, file retention, production settings, Docker, Redis and backups.
- Added attendance regression tests and new database migrations.
