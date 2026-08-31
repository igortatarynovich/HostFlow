# OL-2D — Predecessor evidence & rollback class

**Status:** **DEFERRED_BY_INITIAL_BASELINE / NOT EXECUTED** — 2026-08-31
**Phase class:** platform
**Slice:** OL-2D (predecessor definition + retain store; rehearsal not executed)
**Track:** Launch-ops
**Parents:** [OL-2A contract](operate-launch-ol2-deploy-contract.md) C-4…C-7 · [OL-2B](operate-and-launch.md) · [RB-3](../../runbooks/README.md)

> This is **not a FAIL**. The cause is structural: live production does not
> satisfy the release identity contract, so a predecessor cannot be proven
> without falsifying provenance. Rehearsal becomes executable on the release
> *after* the first procedure-built, retained, tagged baseline.
>
> No tag is created by this document. A tag without a rollbackable predecessor
> is a gate bypass ([C-5](operate-launch-ol2-deploy-contract.md)).
> `11f1c845` is a retained throwaway pair, **not** a baseline release.

---

## What counts as a rollbackable predecessor

A predecessor is a **deployable state**, not “the previous commit” and not “the
previous tag”. All of the following must hold:

1. **Backend artefact identity** — a container image whose identity is its
   digest, built from a clean checkout, code inside the image (no rw source
   bind-mount), OCI revision label present, no secrets ([C-1](operate-launch-ol2-deploy-contract.md)).
2. **Frontend artefact identity** — an immutable tree with a content hash and
   `build.json`, published atomically outside the live document root ([C-2](operate-launch-ol2-deploy-contract.md)).
3. **Documented migration state** — Alembic head recorded for that deploy, and
   the rollback class of the *next* release decided from the path between the
   two heads ([C-7](operate-launch-ol2-deploy-contract.md)).
4. **Launchable through the release compose path** — `deploy/compose.release.yml`
   (or its successor), not the production bind-mount compose.
5. **Retained by digest** — both artefacts still loadable without a rebuild
   ([C-6](operate-launch-ol2-deploy-contract.md), [C-1.5](operate-launch-ol2-deploy-contract.md)).
6. **Execution record** — a dated row that the state actually ran and passed
   smoke. A built image that never served a working login is not a predecessor.

If the current production deployment fails any of 1–4, it **must not** be
named as the predecessor in order to have something to roll back to.

---

## Production measurement (2026-08-31) — not a predecessor

Measured on the live compose project `hostflow` on this host. Read-only.

| Axis | Measured | Release contract |
|---|---|---|
| Backend source | `/opt/HostFlow/backend` bind-mounted **rw** at `/app` | **FAIL C-1.2** |
| Backend image | `hostflow-backend:latest` `sha256:b042430bd9b4…`, created **2026-08-28T11:18:48Z**. No `org.opencontainers.image.revision` | **FAIL C-1.3** |
| Backend `/build` | `GET /build` returns the SPA `index.html` (no endpoint) | **FAIL C-3** |
| Checkout | `453d45bd` `fix(candidates): accept tenant funnel stage codes on PATCH` — this is the bind-mount tree, not the image | not an artefact identity |
| Frontend served | Caddy bind-mounts `/opt/HostFlow/hostflow-frontend/dist`. `index.html` mtime **2026-08-31 10:36:53Z**, bundle `index-CmDzw3o3.js`, **no `build.json`** | **FAIL C-2.4**; provenance unknown |
| `/var/www/hostflow-frontend` | newest `index.html` **2026-07-31** — still not what Caddy serves | irrelevant to rollback |
| Live Alembic | `202608250002_merge_e5_drop_and_adr036_heads` | recorded; not a release head |
| Live `role` enum | `superadmin` **present** (historical hand-fix, not `202608310001`) | cannot be used as “the migration ran” |
| Live `users.preferences` | `NOT NULL`, **no server default** | same defect OL-2B closed in-graph |
| Compose / config | `docker-compose.yml` last committed `5baa9988` (2026-08-25); sha256 `321020bf…`. Caddyfile sha256 `200fd084…` | not the release compose |
| Git tags | **zero** | no `release/vX.Y.Z` |

**Classification: legacy unversioned deployment.**

There is no commit that can be proven to be “what production is”. The image is
three days older than the bind-mount tree; the frontend was overwritten in
place today without metadata; `/build` does not exist. Tagging `453d45bd`
(or any other SHA) as `release/v0.1.0` would invent a predecessor.

---

## Candidate vs a manufacturable prior tree

**Candidate** for the next rollback pair, when one exists:

| Field | Value |
|---|---|
| Composite revision | `11f1c84586c0e96538e7a27e0d14c1617d5a3a8f` (OL-2A `40fa8160` + cherry-pick of first-admin `992a8a4d`) |
| Backend digest (local Id) | `sha256:be7ebfa75705b817966d668a0847aebb459f83e3b89974841a0466782b5caeb6` |
| Frontend tree | `sha256:ba19d410344b1a21b6176df66c3402af7123f9e4e2761d3b74fccc5179c2e2e0` |
| Alembic head | `202608310001_bootstrap_admin_schema` |
| OL-2B | empty-volume pass, login 200, `/build` = `11f1c845…` — **PASS_IMPLEMENTATION / NOT EXECUTED** |

`992a8a4d` alone is not a release artefact: it has no `GET /build` and no
release compose. Baking that SHA into an OL-2A image would violate C-3.

**Prior tree that is *not* a predecessor** (named so it is not used as one):

| Field | Value | Why it is not a predecessor |
|---|---|---|
| `40fa8160` image | still on the daemon as dangling `sha256:ec334c15672c…`, revision label `40fa8160…` | never had an empty-volume release-compose smoke with a matching frontend and a recorded login; pruneable (C-1.5 fail) |
| `7cb67703` image | identity JSON remains; image `sha256:44f8f557…` was **pruned** | cannot be redeployed without rebuild — C-6 fail |
| Second OL-2B pass | `40fa8160` image + **uncommitted** `202608310001` | dirty worktree; discarded as OL-2B evidence |

No tag is minted on `11f1c845` or `40fa8160` here. `11f1c845` may become the
**first baseline** once it is retained and a *later* candidate is deployed by
the same procedure. That later pair is when rollback rehearsal becomes
executable.

---

## Migration compatibility class (`40fa8160` → `11f1c845`)

Alembic path is one revision:

`202608250002_merge_e5_drop_and_adr036_heads` → `202608310001_bootstrap_admin_schema`

| Change | Kind | Symmetric downgrade? |
|---|---|---|
| `ALTER TYPE role ADD VALUE IF NOT EXISTS 'superadmin'` | expand-only | **No.** PostgreSQL cannot drop an enum label. |
| `ALTER TABLE users ALTER COLUMN preferences SET DEFAULT '{}'::jsonb` | expand-only | Yes (`DROP DEFAULT`) — not required for artefact rollback |

**Class: `artefact-reversible` (backward-compatible schema).** Not
`schema-downgrade-required`. Not `restore-only`. Not “code-only” — a migration
did run.

Rollback of `11f1c845` → `40fa8160` **leaves the candidate schema in place**.
That is allowed only if `40fa8160` code works against `202608310001`.

**Compatibility evidence (not a rehearsal):** the 2026-08-31 second throwaway
pass ran image `40fa8160` / `ec334c15…` against a database already at
`202608310001`. Seed created `admin@hostflow.dev`; `POST /auth/login` returned
200. The old seed INSERT (`role=superadmin`, no `preferences` column) succeeds
once the default and the enum label exist — measured again on the clean pass
and covered by `backend/tests/auth/test_bootstrap_admin_schema.py` on #336.
Old `main.py` still swallows seed errors; that does not break login once the
row exists.

Therefore: rolling back **artefacts** after this migration is the intended
path. Rolling back the **schema** is not possible for the enum label and is
not required.

---

## Retained-artefact mechanism (C-1.5 minimum)

Local daemon tags are not retention: `44f8f557…` was pruned the same day it
was built. A rollback that says `docker pull` / `docker build 40fa8160` has
already failed C-6.

**Minimum store** (this slice): a directory of immutable blobs, default
`/var/lib/hostflow/artefact-store`, written by
[`scripts/deploy/retain-release-artefacts.sh`](../../../scripts/deploy/retain-release-artefacts.sh)
and reloaded by
[`scripts/deploy/load-release-artefacts.sh`](../../../scripts/deploy/load-release-artefacts.sh).

- Backend: `docker save` of the image **Id** (`sha256:…`) to
  `images/<hex>.tar`. Re-retain of the same digest is idempotent. A different
  payload at the same path is refused.
- Frontend: tar of the published tree to `frontend/<tree-hash>.tar`. Tree
  identity is [`frontend-tree-hash.sh`](../../../scripts/deploy/frontend-tree-hash.sh)
  (locale `sort`), not Python code-point order.
- Manifest: `manifests/<revision>.json` names both identities and the Alembic
  head. It does not replace the running `/build` query.

A registry may replace this store later. Until then, **if the blob is missing,
rollback has failed**. There is no rebuild fallback. Proven 2026-08-31: load of
an absent digest exits 3 and prints that rebuild is not a fallback.

**First retained pair (not a predecessor, not a tag):**

| Field | Value |
|---|---|
| Store | `/var/lib/hostflow/artefact-store` |
| Backend blob | `images/be7ebfa75705b817966d668a0847aebb459f83e3b89974841a0466782b5caeb6.tar` |
| Frontend blob | `frontend/ba19d410344b1a21b6176df66c3402af7123f9e4e2761d3b74fccc5179c2e2e0.tar` |
| Manifest | `manifests/11f1c84586c0e96538e7a27e0d14c1617d5a3a8f.json` |

This store does **not** make `11f1c845` a predecessor and does **not** make it
a baseline release. It only proves the retain mechanism against a throwaway
pair. A baseline exists only after the procedure runs on the trusted base:
build → retain → independent RB-2 → `release/v*`. `11f1c845` is a local walk
commit and cannot be tagged under C-5.

---

## Rehearsal verdict

| Step | Done? |
|---|---|
| Deploy historical production as predecessor | **No** — not a contract state |
| Deploy `40fa8160` as predecessor | **No** — no honest execution record; image not retained by policy (dangling only) |
| Deploy `11f1c845` → migrate → rollback to a prior retained pair | **Not started** — no prior pair |
| Formal OL-2D close | **No** — **DEFERRED_BY_INITIAL_BASELINE / NOT EXECUTED** |

**Correct outcome:** not a FAIL. The first trusted-base release that is built,
retained, and deployed through the release path **establishes the rollback
baseline**. Rollback rehearsal becomes executable on the **next** release.
Authorising a tag now would be a fictitious first tag.

OL-2C (CI parity) remains open and is a named residual, not a substitute
predecessor. No `release/v*` tag.

---

## RB-3 rule — expand-only migrations

Locked before the operator procedure is written, so a future operator cannot
treat rollback as a symmetric downgrade.

For a release whose rollback class is `artefact-reversible` because its
migrations are **expand-only** (example: `202608310001_bootstrap_admin_schema`
— `ALTER TYPE … ADD VALUE` plus a column default):

1. Rollback **redeploys the retained predecessor artefacts** (image digest +
   frontend tree hash).
2. Rollback **does not** run `alembic downgrade`. PostgreSQL cannot drop an
   enum label; a downgrade script that pretends it can is a contract violation.
3. The candidate schema stays in place. Predecessor code must already have
   been proven to run against that schema (compatibility test), or the
   release must have been declared `restore-only`.

This rule is part of [C-7](operate-launch-ol2-deploy-contract.md) and of RB-3
once that runbook exists. It applies even while RB-3 is MISSING.

---

## Blocker

**No rollbackable predecessor exists.** Production is a legacy unversioned
deployment. C-1.5 was open; the local store above is the minimum close of that
gap for *future* pairs. RB-3 remains unwritten as an operator procedure until
a second retained release exists to name in it.

---

## History

- 2026-08-31: Production measured; classified legacy unversioned. Candidate
  `11f1c845` recorded as the first contract-satisfying throwaway state, not as
  a predecessor. Migration class `artefact-reversible` for `202608310001`.
  Local store retains that pair by digest. Status
  **DEFERRED_BY_INITIAL_BASELINE / NOT EXECUTED**. No tag.
