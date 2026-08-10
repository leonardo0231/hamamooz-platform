# Technology Stack

## Runtime Summary

| Area | Value | Evidence |
|---|---|---|
| Backend language/runtime | Python >=3.12,<3.14 | `Backend/pyproject.toml` |
| Frontend language/runtime | TypeScript on Node >=20 | `Frontend/package.json` |
| Backend package tooling | pip requirements; `uv.lock` is present | `Backend/requirements/dev.txt`, `Backend/uv.lock` |
| Frontend package tooling | npm lockfile | `Frontend/package-lock.json` |
| Containers | Docker Compose, Python and Node image builds | `docker-compose.yml`, `Backend/Dockerfile`, `Frontend/Dockerfile` |

## Production Frameworks and Dependencies

| Dependency | Version | Role | Evidence |
|---|---:|---|---|
| Django | 5.2.16 | API application | `Backend/pyproject.toml` |
| Django REST Framework | 3.16.0 | REST API | `Backend/pyproject.toml` |
| Celery with Redis | 5.6.3 | Background jobs | `Backend/pyproject.toml` |
| PostgreSQL driver | psycopg 3.2.9 | Database access | `Backend/pyproject.toml` |
| Nginx | container proxy/static server | Frontend delivery and API proxy | `Frontend/nginx.conf` |
| esbuild/TypeScript | 0.28.1/5.8.3 | Frontend build/type check | `Frontend/package.json` |

## Development Toolchain

| Tool | Purpose | Evidence |
|---|---|---|
| Ruff | Python lint and format | `Backend/pyproject.toml` |
| pytest/pytest-django/pytest-cov | Backend tests and coverage | `Backend/pyproject.toml` |
| Node test runner | Frontend tests | `Frontend/package.json` |
| GitHub Actions | CI | `.github/workflows/backend-ci.yml`, `.github/workflows/frontend-ci.yml` |

## Key Commands

```powershell
cd Backend; .\.venv\Scripts\python -m pytest
cd Frontend; npm ci; npm run typecheck; npm run lint; npm test
docker compose up --build -d
```

## Environment and Config

Configuration is supplied by root and component `.env.example` files plus Django settings modules. The Compose file supplies local PostgreSQL, Redis, Celery and frontend defaults; production secret values are not present in tracked configuration.

## Evidence

- `Backend/pyproject.toml`
- `Frontend/package.json`
- `docker-compose.yml`
