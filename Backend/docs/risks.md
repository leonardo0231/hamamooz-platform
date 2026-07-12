# Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Cross-branch data leakage | Critical | centralized scope policy, scoped querysets, object/service/task checks, negative tests |
| Formula drift | High | immutable formula versions and reproducible calculation results |
| Partial imports | High | validation phase, transaction boundary, file hash and idempotency key |
| Duplicate async reports | Medium | unique job keys, idempotent tasks and locked state transitions |
| RTL PDF font/render differences | Medium | bundled deployment font policy and rendered PDF regression tests |
| Main branch initialized because repository was empty | Low | only minimal root commit; all backend work continues on feature branches |
| Frontend contract drift | High | validated OpenAPI, changelog and explicit migration guidance |
