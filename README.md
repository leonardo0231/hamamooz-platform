# HamAmoz Platform

HamAmoz is a multi-branch school-management platform. It provides a Django REST API for academic operations, attendance, reporting, imports, and scoped access control, plus a TypeScript browser frontend generated against the committed OpenAPI contract.

## Architecture

```text
Browser -> Frontend (Nginx, port 5173) -> /api proxy -> Django API (port 8000)
                                                    -> PostgreSQL
                                                    -> Redis cache / Celery broker
                                                    -> Celery worker and beat
```

The source tree is a monorepo:

```text
Backend/       Django REST Framework service, Celery tasks, migrations, tests
Frontend/      TypeScript frontend and static Nginx container
contracts/     Generated OpenAPI contract and API changelog
docs/          Shared integration documents
```

## Prerequisites

- Docker Engine with the Compose plugin for the supported local stack
- Python 3.12 or 3.13, PostgreSQL, and Redis only for non-Docker backend development
- Node.js 20+ and npm for non-Docker frontend development

## Environment

Create a local configuration file from the committed template:

```powershell
Copy-Item .env.example .env
```

Set a unique `DJANGO_SECRET_KEY` and a matching value for `POSTGRES_PASSWORD` and the password portion of `DATABASE_URL`. Do not commit `.env`.

Important variables include `DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ALLOWED_ORIGINS`, `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `USE_S3`, `HAMAMOOZ_API_PORT`, and `HAMAMOOZ_FRONTEND_PORT`. The complete backend templates are in `Backend/.env.example` and `Backend/.env.production.example`.

## Docker setup

```powershell
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

Default URLs:

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api/v1/ |
| API readiness | http://localhost:8000/api/v1/health/ready/ |
| Swagger | http://localhost:8000/api/v1/docs/ |
| ReDoc | http://localhost:8000/api/v1/redoc/ |
| Admin | http://localhost:8000/admin/ |

The frontend uses `/api/v1/` at runtime; Nginx proxies that route to the internal `web:8000` service. PostgreSQL, both Redis services, and persistent media/static data use named Docker volumes.

For a local port conflict, override a port for that invocation, for example:

```powershell
$env:HAMAMOOZ_FRONTEND_PORT='8181'; docker compose up -d frontend
```

Stop services without removing persistent volumes:

```powershell
docker compose down
```

To remove the local volumes as well (this deletes local database and media data):

```powershell
docker compose down --volumes
```

## Local development

Backend:

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements\dev.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

Frontend:

```powershell
cd Frontend
npm ci
npm run dev
```

The frontend development default API URL is `http://localhost:8000/api/v1/`.

## Testing and contract generation

```powershell
cd Frontend
npm run typecheck
npm run lint
npm test

cd ..\Backend
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python manage.py check
.\.venv\Scripts\python -m pytest --cov=hamamooz --cov-report=term-missing
.\scripts\generate_openapi.sh ..\contracts\openapi.yaml
```

`contracts/openapi.yaml` is generated from the backend and must not be edited manually.

## Troubleshooting

- Use `docker compose logs --tail=100` to inspect service startup.
- If a host port is in use, set `HAMAMOOZ_API_PORT` or `HAMAMOOZ_FRONTEND_PORT` to an available port before `docker compose up`.
- The `release` service runs migrations and `collectstatic`; `web`, `worker`, and `beat` wait for it.
- Use PostgreSQL rather than SQLite for tests that require real row locking.

## Contributing

Keep backend code in `Backend/`, frontend code in `Frontend/`, and regenerate the OpenAPI contract whenever an API change affects clients. Run the relevant checks before opening a pull request and include migration, permission/scope, and contract impacts.

## License

No license file is currently present. Obtain the repository owner’s permission before redistribution or derivative use.
