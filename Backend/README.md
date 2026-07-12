# HamAmooz Backend

Django REST Framework backend for the multi-branch school platform. The backend is a modular monolith and all API routes are versioned under `/api/v1/`.

## Current slice

Slice 0 establishes the executable backend foundation: custom user model, JWT authentication, PostgreSQL-ready settings, Redis/Celery wiring, optional MinIO/S3 storage, health/readiness probes, OpenAPI, tests, linting, Docker and backend-only CI.

Business modules for organizations, schools, enrollment, scores, calculations, imports and reports are intentionally deferred to their ordered MVP slices.

## Local setup

```bash
cd Backend
cp .env.example .env
make setup
make migrate
make run
```

Swagger: `http://localhost:8000/api/v1/docs/`

ReDoc: `http://localhost:8000/api/v1/redoc/`

Django Admin: `http://localhost:8000/admin/`

## Docker

```bash
cd Backend
cp .env.example .env
make docker-up
```

The compose stack contains PostgreSQL, Redis, MinIO, API and Celery worker. Nginx is available through the `production` profile.

## Quality commands

```bash
make lint
make format-check
make test
make schema
make check
```

## Settings

- Development: `config.settings.development`
- Test: `config.settings.test`
- Production: `config.settings.production`

Production refuses to start with the development secret. Secrets must be supplied through environment variables and must never be committed.

## Documentation map

See `docs/` for requirements traceability, architecture, ERD, permissions, API contract, security, assumptions, risks and vertical-slice backlog.
