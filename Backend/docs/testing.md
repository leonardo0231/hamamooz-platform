# Testing Strategy

Slice tests use pytest and pytest-django. Local tests default to an in-memory SQLite database and LocMem cache only when infrastructure URLs are absent. CI explicitly runs against PostgreSQL and Redis.

Required test layers across MVP: model constraints, services, APIs, permissions, object permissions, cross-branch isolation, calculations, score workflow, imports, Celery tasks, reports, audit, backup/restore, regression and load tests.

Commands:

```bash
make test
make lint
make format-check
make typecheck
make schema
make check
```
