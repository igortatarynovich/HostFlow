# Backend pytest DB reachability (docker) — open debt

**Status:** **open — dev-environment only.** No longer a merge blocker: `integration/release-product-a-b` → `main` already merged 2026-08-26 ([#326](https://github.com/igortatarynovich/HostFlow/pull/326)), and CI does not use the docker-compose pytest path (`backend-ci.yml` / `backend-regression.yml` run against a service Postgres).  
**Date:** 2026-07-15 · reassessed 2026-08-28  
**Scope:** local `docker compose exec backend pytest` only. `conftest.py` rewrites `db` → `127.0.0.1` but never the reverse, so the in-container alembic subprocess still targets the wrong host.  
**Related:** [pytest baseline stabilisation](stabilize-integration-pytest-baseline.md) (test debt SoT) · [unowned work register](../gates/v1-unowned-work-register.md) (quality debt dispositions)

## Symptom

Inside `docker compose exec backend pytest …`, `pytest_sessionstart` runs:

```text
alembic -c /app/alembic.ini upgrade head
```

Alembic (via app settings) connects to `postgresql+psycopg://…@127.0.0.1:5432/hostflow`.  
From the container network, Postgres is reachable as host `db`, not `127.0.0.1` → `Connection refused` → session abort (`INTERNALERROR`).

Manual / compose paths that use `db:5432` work:

- `docker compose exec backend alembic … upgrade head` (default compose env) — PASS  
- repair CLI against Focus Personnel — PASS  

## Required before integration PR → main

Either:

1. Make pytest session alembic use the same DSN as runtime compose (`@db:5432`), or  
2. Publish Postgres on a host network path that `127.0.0.1:5432` resolves correctly from the backend container, **and**  
3. Prove `tests/api/test_questionnaire_ssot_repair.py` green under that configuration (comparative PASS).

Do **not** treat SSOT acceptance as blocked by this env issue once staging API walkthrough PASS is recorded.
