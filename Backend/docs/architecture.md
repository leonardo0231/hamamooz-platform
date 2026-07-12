# Backend Architecture

## Style

A modular monolith is used. Django apps define bounded modules, while cross-module workflows are implemented in explicit service layers. Views and serializers transport and validate data; they do not own complex workflows.

## Runtime

- Django + Django REST Framework API
- PostgreSQL transactional database
- Redis cache and Celery broker/result backend
- S3-compatible object storage for generated files and uploads
- Celery workers for imports, reports and heavy calculations
- Nginx reverse proxy in deployment

## Module direction

`core` provides cross-cutting infrastructure. Domain apps may depend on `core`, but `core` must not import domain models. Domain services expose workflows; asynchronous tasks call those services after re-validating authorization scope.

## Multi-branch rule

School scope is enforced in query construction, API permissions, object checks, services, tasks, exports, report generation, downloads and admin. Serializer hiding is not an authorization control.
