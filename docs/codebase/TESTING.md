# Testing Patterns

## Test Stack and Commands

- Backend: pytest, pytest-django and pytest-cov.
- Frontend: Node built-in test runner plus source lint and deterministic production build.

```powershell
cd Backend; .\.venv\Scripts\python -m pytest --cov=hamamooz --cov-report=xml
cd Frontend; npm test
docker compose config --quiet
```

## Test Layout

Backend tests live in `Backend/tests/` and use `test_*.py`; fixtures are in `Backend/tests/conftest.py`. Frontend tests live in `Frontend/tests/` and use `*.test.mjs`.

## Test Scope Matrix

| Scope | Covered? | Typical target | Notes |
|---|---|---|---|
| Unit | Yes | serializers/services/router/mock-data | Route matching, design tokens, security storage and data assertions |
| Integration | Yes | API, imports, migrations, Redis/Postgres CI services | Backend CI provisions services |
| E2E browser | [TODO] | Full browser journey | No Playwright/Cypress configuration found |
| Docker config | Yes | Compose syntax; image builds in CI | Local builds need Docker daemon |

## Mocking and Isolation Strategy

Backend uses pytest database fixtures and test settings. Frontend tests inspect the Preact module graph, built assets, routes, design tokens, mock-data invariants and security boundaries. Browser E2E is still a separate release gate.

## Coverage and Quality Signals

Backend coverage is enforced at 78%. Frontend CI uploads the production `dist` artifact. The local full coverage run exceeded five minutes in this environment; targeted backend regression tests and the full frontend suite completed.

## Evidence

- `Backend/pyproject.toml`
- `Backend/tests/conftest.py`
- `Frontend/package.json`
- `.github/workflows/backend-ci.yml`
