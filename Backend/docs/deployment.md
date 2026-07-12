# Deployment

The Docker stack supplies API, PostgreSQL, Redis, MinIO and Celery worker. Nginx is provided in the production compose profile.

Production requirements:

- unique strong `DJANGO_SECRET_KEY`
- restricted hosts, CORS and CSRF origins
- managed PostgreSQL/Redis/object storage credentials
- TLS termination and forwarded-proto headers
- database migration as a controlled release step
- separate persistent volumes and backup retention
- centralized logs and external monitoring in the hardening slice
