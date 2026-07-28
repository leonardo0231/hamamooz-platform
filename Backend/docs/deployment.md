# Deployment

The Docker stack supplies API, PostgreSQL, Redis, MinIO and Celery worker. Nginx is provided in the production compose profile.

Start production configuration from `.env.production.example`. Production settings fail fast for
short/placeholder application, PostgreSQL or S3 secrets, missing explicit allowed hosts and wildcard
hosts. Compose also refuses to start without database and object-storage credentials.

Production requirements:

- unique strong `DJANGO_SECRET_KEY`
- restricted hosts, CORS and CSRF origins
- managed PostgreSQL/Redis/object storage credentials
- TLS termination and forwarded-proto headers
- database migration as a controlled release step
- separate persistent volumes and backup retention
- centralized logs and external monitoring in the hardening slice
- encrypted off-host database/object-storage replication and scheduled full restore drills
