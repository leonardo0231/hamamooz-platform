# Coding Conventions

## Naming Rules

| Item | Rule | Example | Evidence |
|---|---|---|---|
| Python files/functions | snake_case | `validate_comprehensive_workbook` | `Backend/hamamooz/apps/imports/comprehensive.py` |
| Python internal helpers | leading underscore | `_reject_rows_beyond_template_limit` | same file |
| Frontend modules | lowercase/kebab-case | `mock-data.js` | `Frontend/src/` |
| Preact components | PascalCase functions | `DashboardPage` | `Frontend/src/pages/dashboard.js` |
| Environment variables | uppercase snake case | `DATABASE_URL` | `.env.example` |

## Formatting and Linting

- Backend: Ruff uses Python 3.12 targets, 100-character lines, and E/F/I/UP/B/SIM rules.
- Frontend: repository Node lint script, Node test runner and deterministic build validation.
- Commands: `ruff check .`, `ruff format --check hamamooz config tests`, `npm run lint`, `npm test`.

## Import and Module Conventions

Backend imports use Python modules within `config` and `hamamooz`; frontend pages use relative ESM imports. HTTP details stay in `Frontend/src/core/api.js`, outside page components.

## Error and Logging Conventions

Django REST errors are normalized by the frontend API client. Import validation accumulates structured sheet/row errors. Sensitive values such as access tokens are not persisted by the frontend client tests.

## Testing Conventions

Backend tests are `Backend/tests/test_*.py`; frontend tests are `Frontend/tests/*.test.mjs`. Backend coverage is configured at 78% minimum in `Backend/pyproject.toml`.

## Evidence

- `Backend/pyproject.toml`
- `Frontend/package.json`
- `Frontend/src/core/api.js`
