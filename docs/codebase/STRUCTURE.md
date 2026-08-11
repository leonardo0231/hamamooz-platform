# Codebase Structure

## Top-Level Map

| Path | Purpose | Evidence |
|---|---|---|
| `Backend/` | Django API, apps, tests, settings and image | `Backend/manage.py`, `Backend/pyproject.toml` |
| `Frontend/` | TypeScript browser application, tests and Nginx image | `Frontend/package.json`, `Frontend/src/` |
| `contracts/` | Generated OpenAPI contract and changelog | `contracts/README.md` |
| `docs/` | Shared product, Docker and codebase documentation | `docs/product/`, `docs/DOCKER_LOCAL_FA.md` |
| `.github/workflows/` | Backend, frontend and Docker CI | workflow files |
| `scripts/` | Root Compose smoke scripts | `scripts/docker-smoke.ps1`, `scripts/docker-integration-smoke.sh` |

## Entry Points

- Backend runtime: `Backend/manage.py`, `Backend/config/wsgi.py`, and `Backend/config/asgi.py`.
- Background runtime: `Backend/config/celery.py` and Compose `worker`/`beat` services.
- Frontend runtime: `Frontend/src/main.ts`; build selection is `Frontend/scripts/build.mjs`.

## Module Boundaries

| Boundary | What belongs here | What must not be here |
|---|---|---|
| `Backend/hamamooz/apps/*` | Django domain apps, serializers, services and views | Frontend UI |
| `Backend/config/` | Runtime configuration and URL/task bootstrap | Domain rules |
| `Frontend/src/api/` | Generated catalog, endpoint registry and client | Direct page-specific fetches |
| `Frontend/src/pages/` | Route-level UI | Backend persistence |

## Naming and Organization Rules

Python is organized by domain app with snake_case modules. Frontend source uses kebab-case filenames and TypeScript modules. The backend and frontend are separate components in this repository; their shared API boundary is `contracts/openapi.yaml`.

## Evidence

- `README.md`
- `Backend/config/urls.py`
- `Frontend/src/app/routes.ts`
- `docs/product/README.md`
