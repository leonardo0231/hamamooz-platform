# Architecture

## Architectural Style

- Primary style: domain-organized Django modular monolith plus a separate TypeScript frontend.
- Constraints: school/organization scoped access, generated OpenAPI compatibility, and asynchronous import/report work.

## System Flow

```text
Browser -> Frontend/Nginx -> /api proxy -> Django views -> app services/models -> PostgreSQL
                                           -> Celery/Redis -> background imports and reports
```

The frontend central client resolves API routes from the generated catalog. Django routes dispatch to app viewsets, which call services/models. The backend generates `contracts/openapi.yaml`; the frontend catalog generator derives its artifacts from that file.

## Layer/Module Responsibilities

| Module | Owns | Must not own | Evidence |
|---|---|---|---|
| `Frontend/src/api/` | HTTP/auth/scope headers and contract registry | Page layout | `Frontend/src/api/client.ts` |
| Django views/serializers | HTTP/API validation and representation | Browser rendering | `Backend/hamamooz/apps/*/views.py` |
| Django services | Domain workflows | Transport-specific UI | `Backend/hamamooz/apps/imports/services.py` |
| Celery pipeline | Async import processing | Synchronous page state | `Backend/hamamooz/apps/imports/pipeline.py` |

## Reused Patterns

| Pattern | Where found | Why |
|---|---|---|
| Viewset + serializer | Django apps | Consistent REST resources |
| Service layer | imports, evaluations, reports | Domain operations outside views |
| Adapter | import adapters | Interpret workbook formats |
| Generated contract catalog | frontend scripts | Keep endpoint registry tied to OpenAPI |

## Known Architectural Risks

- OpenAPI generation emits one enum-name collision warning; its naming needs an explicit override if stable generated naming becomes required.
- Frontend pages use local response interfaces; tests pin selected shapes to the generated catalog but a full generated TypeScript client is not present.

## Evidence

- `docker-compose.yml`
- `Backend/config/urls.py`
- `Frontend/scripts/generate_contract.py`
