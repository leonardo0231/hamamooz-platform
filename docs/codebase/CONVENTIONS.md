# Coding Conventions

## Naming Rules

| Item | Rule | Example | Evidence |
|---|---|---|---|
| Python files/functions | snake_case | `validate_comprehensive_workbook` | `Backend/hamamooz/apps/imports/comprehensive.py` |
| Python internal helpers | leading underscore | `_reject_rows_beyond_template_limit` | same file |
| TypeScript files | kebab-case | `dashboard-v2.ts` | `Frontend/src/pages/` |
| TypeScript types | PascalCase | `ContractOperation` | `Frontend/src/api/contract.ts` |
| Environment variables | uppercase snake case | `DATABASE_URL` | `.env.example` |

## Formatting and Linting

- Backend: Ruff uses Python 3.12 targets, 100-character lines, and E/F/I/UP/B/SIM rules.
- Frontend: repository Node lint script and TypeScript `tsc --noEmit`.
- Commands: `ruff check .`, `ruff format --check hamamooz config tests`, `npm run lint`, `npm run typecheck`.

## Import and Module Conventions

Backend imports use Python modules within `config` and `hamamooz`; frontend pages use relative ESM imports. The frontend endpoint registry uses generated operation identifiers instead of literal routes.

## Error and Logging Conventions

Django REST errors are normalized by the frontend API client. Import validation accumulates structured sheet/row errors. Sensitive values such as access tokens are not persisted by the frontend client tests.

## Testing Conventions

Backend tests are `Backend/tests/test_*.py`; frontend tests are `Frontend/tests/*.test.mjs`. Backend coverage is configured at 78% minimum in `Backend/pyproject.toml`.

## Evidence

- `Backend/pyproject.toml`
- `Frontend/package.json`
- `Frontend/src/api/client.ts`
