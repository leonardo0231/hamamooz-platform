# Testing Strategy

Slice tests use pytest and pytest-django. Local tests default to an in-memory SQLite database and LocMem cache only when infrastructure URLs are absent. CI explicitly runs against PostgreSQL and Redis.

Required test layers across MVP: model constraints, services, APIs, permissions, object permissions, cross-branch isolation, calculations, score workflow, imports, Celery tasks, reports, audit, backup/restore, regression and load tests.

The coverage gate is 78% branch-aware coverage. CI additionally audits production dependencies,
validates the OpenAPI schema, exercises Redis/Celery and private S3 connectivity, imports 2,000
students, verifies PostgreSQL row-lock protection against class overbooking, and performs a real
PostgreSQL dump/restore drill.

Commands:

```bash
make test
make lint
make format-check
make typecheck
make schema
make check
```
