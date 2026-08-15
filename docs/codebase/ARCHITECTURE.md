# Architecture

## Architectural Style

- Primary style: domain-organized Django modular monolith plus a separate component-based Preact frontend.
- Constraints: school/organization scoped access, generated OpenAPI compatibility, and asynchronous import/report work.

## System Flow

```text
Browser -> Frontend/Nginx -> /api proxy -> Django views -> app services/models -> PostgreSQL
                                           -> Celery/Redis -> background imports and reports
```

The frontend central client owns authentication refresh, scope headers, timeout and normalized errors. Django routes dispatch to app viewsets, which call services/models. The backend-generated `contracts/openapi.yaml` remains the API source of truth and changes require updating the frontend adapter.

The root integration smoke starts the production-like Compose topology in an isolated project name and exercises health, token authentication, dashboard/student reads, the comprehensive import workflow and report preview through public HTTP routes. It is a baseline verification path, not a second runtime architecture.

## Layer/Module Responsibilities

| Module | Owns | Must not own | Evidence |
|---|---|---|---|
| `Frontend/src/core/` | HTTP/auth/scope, session, routing and runtime configuration | Page layout | `Frontend/src/core/api.js` |
| `Frontend/src/components/` | Shell, charts and accessible UI primitives | Domain persistence | component modules |
| Django views/serializers | HTTP/API validation and representation | Browser rendering | `Backend/hamamooz/apps/*/views.py` |
| Django services | Domain workflows | Transport-specific UI | `Backend/hamamooz/apps/imports/services.py` |
| Celery pipeline | Async import processing | Synchronous page state | `Backend/hamamooz/apps/imports/pipeline.py` |

## Reused Patterns

| Pattern | Where found | Why |
|---|---|---|
| Viewset + serializer | Django apps | Consistent REST resources |
| Service layer | imports, evaluations, reports | Domain operations outside views |
| Adapter | import adapters | Interpret workbook formats |
| Central API adapter | frontend core | Keep page components independent of transport and auth details |

## Known Architectural Risks

- OpenAPI generation emits one enum-name collision warning; its naming needs an explicit override if stable generated naming becomes required.
- Runtime response validation is intentionally lightweight; contract-change CI should add schema-backed adapter tests for changed endpoints.

## Evidence

- `docker-compose.yml`
- `Backend/config/urls.py`
- `Frontend/src/core/api.js`
- `scripts/docker-integration-smoke.sh`
