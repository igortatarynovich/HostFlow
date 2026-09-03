# RB-1 — Deploy a release build

**Status:** **DRAFT / NOT EXECUTED** — 2026-08-31
**Answers:** RR3
**Owner:** igortatarynovich
**Parents:** [Operate & Launch](../specs/tasks/operate-and-launch.md) · [OL-2A contract](../specs/tasks/operate-launch-ol2-deploy-contract.md) · [RB-2](rb-2-migrate-and-bootstrap.md) · [runbook index](README.md)

> Independent-operator execution is the gate. Author walks do **not** count.
> This procedure deploys **retained artefacts**. It does not rebuild. It does
> not tag. It does not touch the live compose project `hostflow`.

---

## What this procedure is

Take a retained pair (backend image digest + frontend tree hash) for one
commit SHA, start it on a throwaway target through
[`deploy/compose.release.yml`](../../deploy/compose.release.yml), apply
migrations from the repository root, and prove the running system:

1. `GET /healthz` → 200
2. `GET /build` → 200 and `revision` equals the SHA in the manifest
3. `POST /api/v1/auth/login` as `admin@hostflow.dev` / `Admin@025` → 200
4. `GET /build.json` from the published frontend → 200 and the same SHA

Identity is the digest. Rollback later names those digests. Rebuilding the
commit is not this procedure and is not a fallback ([C-6](../specs/tasks/operate-launch-ol2-deploy-contract.md)).

The first baseline candidate on the trusted base is
`650c7d114582ede54c2868e08a53ee0ba2797cc7`. Do **not** substitute `11f1c845`.

---

## Preconditions

1. Throwaway compose project **`hostflow-release`**. Never `docker compose -p hostflow down`.
2. Env file **outside** every checkout and build context, mode `0600`, no live
   payment or messaging credentials. Do not copy `/opt/HostFlow/.env`.
   `HOSTFLOW_ENV_FILE` must point at that file. Include
   `HOSTFLOW_AUTH_SEED_ENABLED=1` and a non-production `JWT_SECRET`.
3. At least 10 G free disk.
4. Artefact store holds the manifest and both blobs. Missing blob = failed
   deploy; do not rebuild.
5. A clean checkout of the **same SHA as the manifest** (Alembic scripts only).
   The live tree `/opt/HostFlow` is a bind-mounted production checkout and is
   not this procedure's workspace.
6. Ports `HOSTFLOW_HTTP_PORT` (default 8088) and `HOSTFLOW_DB_PORT` (default
   55435) are free. Default DB port is **not** 5432.

---

## Procedure

Manifest:

```text
/var/lib/hostflow/artefact-store/manifests/<GIT_SHA>.json
```

### 1. Load artefacts (no rebuild)

```bash
export HOSTFLOW_ARTEFACT_STORE=/var/lib/hostflow/artefact-store
backend_id="$(python3 -c 'import json; print(json.load(open("'"$HOSTFLOW_ARTEFACT_STORE"'/manifests/'"$GIT_SHA"'.json"))["backend_image_id"])')"
frontend_hash="$(python3 -c 'import json; print(json.load(open("'"$HOSTFLOW_ARTEFACT_STORE"'/manifests/'"$GIT_SHA"'.json"))["frontend_tree_hash"])')"

bash scripts/deploy/load-release-artefacts.sh backend "$backend_id"
rm -rf /var/lib/hostflow/release-target/frontend
bash scripts/deploy/load-release-artefacts.sh frontend "$frontend_hash" \
  /var/lib/hostflow/release-target/frontend
```

Confirm `docker image inspect --format '{{.Id}}' hostflow-backend:<12-char-sha>`
equals `backend_image_id`. Confirm
`/var/lib/hostflow/release-target/frontend/build.json` carries the same
`revision` as `$GIT_SHA`.

### 2. Start database only, then migrate

Compose starts uvicorn as soon as Postgres is healthy. Seed needs the migrated
schema, so **do not** start backend until Alembic has finished.

```bash
export GIT_SHA=<manifest revision>
export HOSTFLOW_BACKEND_IMAGE=hostflow-backend:${GIT_SHA:0:12}
export HOSTFLOW_ENV_FILE=/path/outside/checkout/env
export HOSTFLOW_FRONTEND_ROOT=/var/lib/hostflow/release-target/frontend
export HOSTFLOW_HTTP_PORT=8088
export HOSTFLOW_DB_PORT=55435

docker compose -p hostflow-release -f deploy/compose.release.yml up -d --no-build db redis
# wait until db is healthy
export ALEMBIC_DATABASE_URL=postgresql+psycopg://hostflow:hostflow@127.0.0.1:${HOSTFLOW_DB_PORT}/hostflow
export SYNC_DATABASE_URL="$ALEMBIC_DATABASE_URL"
alembic -c alembic.ini upgrade heads
alembic -c alembic.ini current   # expect 202608310001_bootstrap_admin_schema on this candidate
```

### 3. Start the application and prove it

```bash
docker compose -p hostflow-release -f deploy/compose.release.yml up -d --no-build
# wait until backend is healthy
curl -fsS "http://127.0.0.1:${HOSTFLOW_HTTP_PORT}/healthz"
curl -fsS "http://127.0.0.1:${HOSTFLOW_HTTP_PORT}/build"
curl -fsS -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: 11111111-1111-1111-1111-111111111111' \
  -d '{"email":"admin@hostflow.dev","password":"Admin@025"}' \
  "http://127.0.0.1:${HOSTFLOW_HTTP_PORT}/api/v1/auth/login"
curl -fsS "http://127.0.0.1:${HOSTFLOW_HTTP_PORT}/build.json"
```

`/build` and `/build.json` must both equal `$GIT_SHA`. A miss is an OL-2C
defect on this path, not a residual.

### 4. Tear down the throwaway

```bash
docker compose -p hostflow-release -f deploy/compose.release.yml down -v
```

Confirm the live project is still up: `docker compose -p hostflow ps`.

---

## What this runbook is not

- Not a production cutover of `/opt/HostFlow`. That host still runs a legacy
  unversioned bind-mount.
- Not RB-2's proof script ([release-proof.sh](../../scripts/deploy/release-proof.sh)
  is the CI / empty-DB half; this runbook is the artefact half).
- Not a rollback (OL-2D remains **DEFERRED_BY_INITIAL_BASELINE / NOT EXECUTED**).
- Not a tag. Tag `release/v*` only after an independent operator records PASS
  on retained artefacts of `650c7d11…` (or a later agreed candidate SHA).

---

## Execution log

| Date | Operator | Target | Build | Observed result |
|---|---|---|---|---|
| 2026-08-31 | author (does **not** count) | `hostflow-release` from store blobs | `650c7d11…` | `/healthz` 200, `/build` SHA, login 200, frontend `build.json` SHA. Live `hostflow` untouched. **NOT EXECUTED** |
