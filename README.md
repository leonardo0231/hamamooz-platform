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

## Docker: full local stack

The root `docker-compose.yml` is the supported local stack. It starts PostgreSQL,
Redis, Django/Gunicorn, migrations, demo bootstrap, Celery worker/beat, and the
Nginx frontend together. No `.env` file is required for the local defaults.

From the repository root run:

```powershell
docker compose up --build -d
```

Then verify the stack:

```powershell
docker compose ps
docker compose logs -f web frontend db
```

Default URLs:

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API through frontend | http://localhost:5173/api/v1/ |
| API direct | http://localhost:8000/api/v1/ |
| API readiness | http://localhost:5173/api/v1/health/ready/ |
| Swagger | http://localhost:5173/api/v1/docs/ |
| ReDoc | http://localhost:5173/api/v1/redoc/ |
| Django admin | http://localhost:5173/admin/ |

The local demo bootstrap is enabled by default and creates this account:

```text
username: admin
password: Admin123!ChangeMe
```

Change those values before sharing the environment. Set `SEED_DEMO=false` to
disable demo data creation. The seed is idempotent and does not reset an
existing administrator password.

### Optional environment overrides

The stack works without `.env`. To override defaults, copy the template:

```powershell
Copy-Item .env.example .env
```

On Linux/macOS:

```bash
cp .env.example .env
```

When `DATABASE_URL` is empty, the Backend entrypoint builds it from `POSTGRES_*`.
Set an explicit URL only when needed, especially for URL-encoded passwords. Do
not commit `.env`. Important overrides include `HAMAMOOZ_API_PORT`,
`HAMAMOOZ_FRONTEND_PORT`, `SEED_DEMO`, `SEED_ADMIN_PASSWORD`, and
`CELERY_WORKER_CONCURRENCY`.

For a port conflict in PowerShell:

```powershell
$env:HAMAMOOZ_FRONTEND_PORT='8181'
docker compose up --build -d
```

### Lifecycle commands

```powershell
# Stop containers and keep data
docker compose down

# Rebuild after source or dependency changes
docker compose up --build -d

# Delete the local database, Redis data, media, and static volumes
docker compose down --volumes

# Open PostgreSQL inside the stack
docker compose exec db psql -U hamamooz -d hamamooz
```

The browser uses the frontend origin for `/api/`, `/media/`, `/static/`, and
`/admin/`. Nginx proxies dynamic requests to the internal `web:8000` service and
serves static/media files from shared named volumes.

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
