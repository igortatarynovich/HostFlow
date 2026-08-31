# OL-2C — CI / RB-2 deployment proof-path

**Status:** **PASS_IMPLEMENTATION** pending full five-assertion proof on this tree — 2026-08-31
**Phase class:** platform
**Slice:** OL-2C
**Track:** Launch-ops
**Parents:** [OL-2A contract](operate-launch-ol2-deploy-contract.md) · [Operate & Launch](operate-and-launch.md) · [RB-2](../../runbooks/README.md)

> One reproducible path for CI and RB-2: fresh PostgreSQL 16 → migrate through
> the canonical Alembic entrypoint → bootstrap → application start →
> `/healthz` 200 → `/build` 200 + SHA → admin login 200.
> Identity is a commit SHA, never the working tree.

---

## What this slice owns

| Decision | Value |
|---|---|
| CI Postgres | `postgres:16-alpine` — same image as `docker-compose.yml` and `deploy/compose.release.yml` |
| Canonical Alembic | **repo-root `alembic.ini`**. Invoke `alembic -c alembic.ini upgrade heads` from the repository root. `backend/alembic.ini` is a compatibility shim for leftover `cd backend && alembic` callers; it is not a second SoT |
| Documents Alembic | `backend/app/modules/documents/alembic.ini` is a **different graph**. Untouched |
| Proof-path | [`scripts/deploy/release-proof.sh`](../../../scripts/deploy/release-proof.sh) + [`.github/workflows/release-proof.yml`](../../../.github/workflows/release-proof.yml) |
| RR6 / #331 | **Not required.** This gate is a deploy-shaped curl path, not the pytest suite. Do not copy #331 |

---

## Proof-path steps

1. Resolve identity: `GIT_SHA` / `GITHUB_SHA` must equal `git rev-parse HEAD`. A dirty tree is refused (CI checkout is clean).
2. `alembic -c alembic.ini upgrade heads` against a freshly created `postgres:16-alpine`.
3. Start the application with `HOSTFLOW_REVISION=$GIT_SHA` (not `git rev-parse` at request time).
4. Assert `GET /healthz` returns 200.
5. Assert `GET /build` returns 200 and JSON `revision` equals `$GIT_SHA`.
6. Assert `POST /api/v1/auth/login` as `admin@hostflow.dev` returns 200.

Missing `/build` or a failed login after #332 and #336 are on the tree is an **OL-2C defect**, not a residual.

---

## What this is not

- Not the first baseline release. That sequence is: merge the release-path PRs → trusted base green → build immutable artefacts → retain by digest → independent RB-2 → tag `release/v*` → that tag is the predecessor of the *next* release ([C-5](operate-launch-ol2-deploy-contract.md)). OL-2D records why rehearsal waits for that second release.
- Not a pytest-suite green. #331 stays its own PR.
- Not RB-2 executed. Same script, different operator.

---

## History

- 2026-08-31: Slice opened and implemented. Canonical Alembic = repo-root `alembic.ini`. CI Postgres aligned to 16-alpine. Proof-path job added.
