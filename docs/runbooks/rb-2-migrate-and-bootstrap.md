# RB-2 — Apply migrations and reach a starting application

**Status:** **DRAFT from first measured pass (2026-08-31)** — not executed for the gate
**Answers:** RR3, [RC condition 4](../specs/gates/release-readiness-gate.md)
**Owner:** igortatarynovich
**Parents:** [Operate & Launch](../specs/tasks/operate-and-launch.md) OL-2B · [OL-2A contract](../specs/tasks/operate-launch-ol2-deploy-contract.md) · [runbook index](README.md)
**Uses:** `scripts/deploy/build-release-artefacts.sh`, `scripts/deploy/publish-frontend.sh`, `deploy/compose.release.yml`

> Written **during** the first throwaway attempt, not before it. Steps that were not actually
> reached are marked STOP, not invented.

---

## Preconditions (measured)

1. A **throwaway** target. Not the production compose project (`hostflow-*` on this host).
2. The OL-2A **release path** is present in the tree you build from (`feat/operate-launch-ol2a-artefact-identity` or a descendant). The trusted base alone does not yet contain it until that PR merges.
3. An env file **outside every checkout and every build context**, mode `0600`, containing **no live payment or messaging credentials**. Copying `/opt/HostFlow/.env` is forbidden.
4. Disk headroom. On 2026-08-31 the production host was at **100% of 75 G** after the release image + frontend build. `postgres:16-alpine` then failed `initdb` (`pg_wal`: no space left). **Do not start this procedure on a host with less than 10 G free.** Building on the production host is a risk to the live stack; the live backend restarted during this pass.
5. Clean git tree in the build checkout (`build-release-artefacts.sh` refuses dirty).

---

## Procedure (as far as it has been walked)

### 1. Build immutable artefacts

From the release-path checkout, clean tree:

```bash
HOSTFLOW_RELEASE_DIR=/var/lib/hostflow/ol2b/artefacts \
HOSTFLOW_BACKEND_IMAGE=hostflow-backend:ol2b \
  bash scripts/deploy/build-release-artefacts.sh
```

**Observed 2026-08-31** on `7cb67703`:

| Artefact | Identity |
|---|---|
| Backend image | `sha256:44f8f557cf8a8c9e57c192897f8f1b0c569f75ea128920e7afd1dc1a0f123adf` (local Id; no registry — C-1.5 still open) |
| Image labels | `org.opencontainers.image.revision=7cb67703…`, `.created=2026-08-31T10:15:48Z` |
| `/app/.env` in that image | **ABSENT** |
| Frontend tree | built; first pass wrote `build.json` into `hostflow-frontend/dist/` instead of `--outDir` (fixed in `40fa8160`) |
| Frontend after the fix | `sha256:506bdda85c3169ac0d349b0ef69bab8b499ff58da393f63c9ba1cc18b8e612cc` with `build.json` `{revision: 7cb67703…}` |

### 2. Publish the frontend atomically

```bash
bash scripts/deploy/publish-frontend.sh \
  /var/lib/hostflow/ol2b/artefacts/frontend/<full-sha> \
  /var/lib/hostflow/releases/frontend
```

Refuses a tree without `build.json`. Swaps `/var/lib/hostflow/releases/frontend/current` as a symlink.

### 3. Start the throwaway stack — **STOP on this host**

```bash
GIT_SHA=<full-sha> BUILD_TIME=<iso> \
HOSTFLOW_BACKEND_IMAGE=hostflow-backend:ol2b \
HOSTFLOW_ENV_FILE=/var/lib/hostflow/ol2b/env \
HOSTFLOW_FRONTEND_ROOT=/var/lib/hostflow/releases/frontend/current \
HOSTFLOW_HTTP_PORT=8088 \
  docker compose -f deploy/compose.release.yml up -d --no-build
```

**Observed:** `hostflow-release-db-1` never became healthy. `initdb` could not create `pg_wal` — no space left on device. Compose then refused to start backend/caddy. The live project was not the compose target; the live backend still restarted (disk pressure). The throwaway stack was taken down with `-v`.

Until a target with disk headroom exists, **do not retry compose on this host.**

### 4. Migrations on Postgres 16 — walked via sidecar

Because compose could not start its own database, a sidecar `postgres:16-alpine` on `127.0.0.1:55432` (already present on the host as the production image) was used. Env scrubbed (`env -i`); all three Alembic URL variables pinned to that port.

```bash
alembic -c alembic.ini upgrade heads
```

**Observed:** exit 0, head `202608250002_merge_e5_drop_and_adr036_heads`. Same result as the 2026-08-31 measurement, now on the OL-2A tree, Postgres 16.

This is the migration half of RC condition 4. It is **not** yet “by the documented procedure” on the release compose path.

### 5. First-admin / bootstrap — **FAIL** (same two errors)

Against that freshly migrated database, the insert `ensure_seed.py` performs:

```
ERROR: invalid input value for enum role: "superadmin"
ERROR: null value in column "preferences" of relation "users" violates not-null constraint
```

A freshly migrated instance still cannot accept the bootstrap admin. The seed swallows this; startup would look healthy. Closing this is still OL-2B work and is **not done**.

### 6. Backend starts / frontend served / `/build` observable — **not reached**

Blocked by step 3. The release **image** answers `HOSTFLOW_REVISION` when run with `docker run --rm --entrypoint sh hostflow-backend:ol2b` (measured, then the image was removed to free disk). The live backend was not queried as evidence.

---

## What this runbook is not

- Not RB-1 (deploy to production).
- Not a rollback (OL-2D).
- Not an execution record that satisfies the gate: the operator of this pass is the author.

---

## Execution log

| Date | Operator | Target | Build | Observed result |
|---|---|---|---|---|
| 2026-08-31 | author (does **not** count) | throwaway attempt on the production host + sidecar `:55432` | `7cb67703` / image `44f8f557…` (later pruned) | Artefacts built; frontend publish works after `40fa8160`; compose STOP (disk); migrate on 16 OK; first-admin FAIL; `/build` on a running release stack not reached |
