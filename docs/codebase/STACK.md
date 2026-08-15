# Technology Stack

## Runtime Summary

| Area | Value | Evidence |
|---|---|---|
| Backend language/runtime | Python >=3.12,<3.14 | `Backend/pyproject.toml` |
| Frontend language/runtime | JavaScript ES Modules on Node >=20 | `Frontend/package.json` |
| Backend package tooling | pip requirements; `uv.lock` is present | `Backend/requirements/dev.txt`, `Backend/uv.lock` |
| Frontend package tooling | Dependency-free Node build; vendored runtime with licenses | `Frontend/scripts/build.mjs`, `Frontend/src/vendor/` |
| Containers | Docker Compose, Python and Node image builds | `docker-compose.yml`, `Backend/Dockerfile`, `Frontend/Dockerfile` |

## Production Frameworks and Dependencies

| Dependency | Version | Role | Evidence |
|---|---:|---|---|
| Django | 5.2.16 | API application | `Backend/pyproject.toml` |
| Django REST Framework | 3.16.0 | REST API | `Backend/pyproject.toml` |
| Celery with Redis | 5.6.3 | Background jobs | `Backend/pyproject.toml` |
| PostgreSQL driver | psycopg 3.2.9 | Database access | `Backend/pyproject.toml` |
| Nginx | container proxy/static server | Frontend delivery and API proxy | `Frontend/nginx.conf` |
| Preact/HTM | 10.29.8/3.1.1 | Component rendering and templates | `Frontend/src/vendor/` |

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
cd Frontend; npm run lint; npm test
docker compose up --build -d
```

## Environment and Config

Configuration is supplied by root and component `.env.example` files plus Django settings modules. The Compose file supplies local PostgreSQL, Redis, Celery and frontend defaults; production secret values are not present in tracked configuration.

## Evidence

- `Backend/pyproject.toml`
- `Frontend/package.json`
- `docker-compose.yml`
