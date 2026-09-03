# RB-2 — Apply migrations and reach a starting application

**Status:** **DRAFT / NOT EXECUTED** — 2026-08-31
**Answers:** RR3, [RC condition 4](../specs/gates/release-readiness-gate.md)
**Owner:** igortatarynovich
**Parents:** [Operate & Launch](../specs/tasks/operate-and-launch.md) · [OL-2C proof-path](../specs/tasks/operate-launch-ol2c-ci-parity.md) · [OL-2A contract](../specs/tasks/operate-launch-ol2-deploy-contract.md) · [runbook index](README.md)

> Independent-operator execution is the gate. Author walks do **not** count.
> Do **not** rebuild `11f1c845`. The first baseline is a later trusted-base HEAD.

---

## What this procedure is

The same path CI and a human operator share:

1. A **specific commit SHA** on the trusted base (not a dirty working tree).
2. Fresh `postgres:16-alpine`.
3. `alembic -c alembic.ini upgrade heads` from the repository root.
4. Application start with `HOSTFLOW_REVISION=$GIT_SHA`.
5. `GET /healthz` → 200.
6. `GET /build` → 200 and `revision` equals that SHA.
7. `POST /api/v1/auth/login` as `admin@hostflow.dev` / `Admin@025` → 200.

The script is [`scripts/deploy/release-proof.sh`](../../scripts/deploy/release-proof.sh).
For a release candidate the same SHA is then built into immutable artefacts and
retained by digest (`build-release-artefacts.sh`, `retain-release-artefacts.sh`).

---

## Preconditions

1. Throwaway target. Not the production compose project (`hostflow-*`).
2. Env file **outside** every checkout and build context, mode `0600`, no live
   payment or messaging credentials. Do not copy `/opt/HostFlow/.env`.
3. At least 10 G free disk.
4. Clean git tree. `GIT_SHA` / `GITHUB_SHA` equals `git rev-parse HEAD`.
5. Empty volumes. A database migrated from a dirty worktree is not this procedure.

---

## Procedure

### A. Empty-target proof (required)

```bash
export GIT_SHA=$(git rev-parse HEAD)
export DATABASE_URL=postgresql+asyncpg://hostflow:hostflow@127.0.0.1:<throwaway>/hostflow
export SYNC_DATABASE_URL=postgresql+psycopg://hostflow:hostflow@127.0.0.1:<throwaway>/hostflow
export ALEMBIC_DATABASE_URL="$SYNC_DATABASE_URL"
export HOSTFLOW_AUTH_SEED_ENABLED=1
bash scripts/deploy/release-proof.sh
```

All five assertions must pass. A `/build` miss or a failed login is an OL-2C defect.

### B. Immutable artefacts (required before a tag)

```bash
bash scripts/deploy/build-release-artefacts.sh
HOSTFLOW_ARTEFACT_STORE=/var/lib/hostflow/artefact-store \
  bash scripts/deploy/retain-release-artefacts.sh backend "$HOSTFLOW_BACKEND_IMAGE"
HOSTFLOW_ARTEFACT_STORE=/var/lib/hostflow/artefact-store \
  bash scripts/deploy/retain-release-artefacts.sh frontend "$HOSTFLOW_RELEASE_DIR/frontend/$GIT_SHA"
```

Rollback later names those digests. It does not rebuild the commit.
Expand-only migrations (including `202608310001_bootstrap_admin_schema`) do
**not** run `alembic downgrade` — [OL-2D / RB-3](../specs/tasks/operate-launch-ol2d-predecessor.md#rb-3-rule--expand-only-migrations).

### C. Optional compose walk

The artefact half is [RB-1](rb-1-deploy-release-build.md): load from the store,
start `db`/`redis` only, host-side Alembic, then backend/caddy.
`HOSTFLOW_DB_PORT` (default 55435) is published for that Alembic step.

---

## What this runbook is not

- Not RB-1 (production deploy).
- Not a rollback (OL-2D remains **DEFERRED_BY_INITIAL_BASELINE / NOT EXECUTED**).
- Not a tag. Tag only after an independent operator records PASS on retained artefacts of this exact HEAD.

---

## Execution log

| Date | Operator | Target | Build | Observed result |
|---|---|---|---|---|
| 2026-08-31 | author (does **not** count) | throwaway | `11f1c845` composite | Historical OL-2B evidence only. **Not** a baseline candidate |
| 2026-08-31 | author (does **not** count) | throwaway PG16 `:55434` | `802f3854` (#338 on then-tip) | Five assertions green (`/healthz`, `/build` SHA, login 200). **NOT EXECUTED** |
