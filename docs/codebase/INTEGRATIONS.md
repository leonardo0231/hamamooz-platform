# External Integrations

## Integration Inventory

| System | Type | Purpose | Auth model | Criticality | Evidence |
|---|---|---|---|---|---|
| PostgreSQL | DB | Persistent application data | `DATABASE_URL`/Postgres env | High | `docker-compose.yml` |
| Redis | Queue/cache | Celery broker/result/cache services | Redis URLs | High | `docker-compose.yml` |
| Celery | Worker | Imports, reports and scheduled work | Internal broker connection | High | `Backend/config/celery.py` |
| S3-compatible storage | Object storage | Optional media storage | AWS env variables | Medium | `Backend/config/settings/base.py` |
| Sentry | Monitoring | Optional Django error reporting | `SENTRY_DSN` | Medium | `Backend/config/settings/base.py` |
| Nginx | Proxy | Frontend delivery and API proxy | Internal Compose network | High | `Frontend/nginx.conf` |

## Data Stores

| Store | Role | Access layer | Key risk | Evidence |
|---|---|---|---|---|
| PostgreSQL | Domain records | Django ORM | Scoped data correctness | `Backend/config/settings/base.py` |
| Redis | Cache/Celery | Celery/Redis URLs | Broker readiness | `docker-compose.yml` |
| S3/filesystem | Uploads/reports | Django storage | Deployment credential/configuration | `Backend/config/settings/base.py` |

## Secrets and Credentials Handling

Tracked `.env.example` files contain templates/local values; actual `.env` is ignored. CI uses test-only service credentials and does not reference production secrets. Rotation process: [TODO].

## Reliability and Failure Behavior

Import Celery tasks retry `OSError` with exponential delays. Docker Compose uses health checks for database, Redis, web and frontend services. Circuit breaking: [TODO].

## Observability for Integrations

Audit events and optional Sentry are configured in backend source. Metrics/tracing backend: [TODO].

## Evidence

- `.env.example`
- `Backend/hamamooz/apps/imports/tasks.py`
- `docker-compose.yml`
