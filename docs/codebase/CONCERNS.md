# Codebase Concerns

## Top Risks (Prioritized)

| Severity | Concern | Evidence | Impact | Suggested action |
|---|---|---|---|---|
| High | Full local backend coverage run exceeds five minutes | local verification output | Complete suite status is not yet available locally | Run it in CI or investigate slow tests |
| High | New Compose integration smoke has no recorded green remote run yet | `.github/workflows/backend-ci.yml`, `scripts/docker-integration-smoke.sh` | F0 cannot be accepted without runtime evidence | Require the `integration-smoke` check on the next PR/push |
| Medium | Bash/WSL ممکن است Docker Desktop integration نداشته باشد | نخستین اجرای smoke با `docker` در WSL شکست خورد؛ اجرای `DOCKER_BIN=docker.exe` green شد | developer محلی ممکن است smoke را با binary نادرست اجرا کند | در WSL از `DOCKER_BIN=docker.exe` استفاده شود یا Docker Desktop WSL integration فعال شود |
| Medium | Frontend response interfaces are local rather than generated | `Frontend/src/pages/dashboard-v2.ts` | Contract drift risk | Adopt generated operation types/runtime validation |

## Technical Debt

| Debt item | Why it exists | Where | Risk if ignored | Suggested fix |
|---|---|---|---|---|
| Duplicate workbook helpers | Parallel import hardening work | `comprehensive.py`, `comprehensive_hardening.py` | Normalization divergence | Extract shared helpers |
| Structured row dictionaries | Flexible workbook parsing | imports modules | Fragile string-key coupling | Introduce `TypedDict`/dataclasses |

## Security Concerns

| Risk | OWASP category | Evidence | Current mitigation | Gap |
|---|---|---|---|---|
| Local defaults are unsafe for production | A05 | `.env.example` | Comments mark local-only values | Enforce deployment secret provisioning |
| Optional object storage/monitoring secrets | A02 | `Backend/config/settings/base.py` | Environment configuration | Rotation policy [ASK USER] |

## Performance and Scaling Concerns

| Concern | Evidence | Current symptom | Scaling risk | Suggested improvement |
|---|---|---|---|---|
| Import workbook limits | `comprehensive.py` | Fixed template ranges | Large imports need explicit limits | Keep server validation and document supported size |
| Full backend suite duration | local verification | >5 minutes | Slow feedback | Profile tests in CI |

## Fragile/High-Churn Areas

| Area | Why fragile | Churn signal | Safe change strategy |
|---|---|---|---|
| Backend settings/CI | Runtime and pipeline centralization | scan high-churn list | Change with full backend/CI checks |
| Import services/views | Validation and persistence coupling | scan high-churn list | Add focused regression tests first |
| Frontend API catalog | Generated API boundary | scan high-churn list | Regenerate only from backend contract |

## `[ASK USER]` Questions

1. [ASK USER] What is the required timeout/target duration for the full backend suite in CI?
2. [ASK USER] Should frontend API interfaces be replaced with a generated typed client, or is contract-shape test coverage sufficient for the current release?
3. [ASK USER] What documented production secret-rotation policy should the repository follow?

## Evidence

- `docs/codebase/.codebase-scan.txt`
- `Backend/hamamooz/apps/imports/comprehensive.py`
- `Frontend/src/pages/dashboard-v2.ts`
