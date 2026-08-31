# OL-2A — Deploy contract & artefact identity

**Status:** **ACTIVE (contract drafted, not yet enforced)** — 2026-08-31
**Phase class:** platform
**Slice:** OL-2A, first of four inside [OL-2](operate-and-launch.md)
**Track:** Launch-ops
**Parents:** [Operate & Launch](operate-and-launch.md) · [Release Readiness Gate](../gates/release-readiness-gate.md) RC conditions 1–4 · [Launch Ownership Gate](../gates/launch-ownership-gate.md) (OL1-C1, OL1-C2) · [Runbook index](../../runbooks/README.md) RB-1…RB-3

> Release semantics come **before** tags. This slice defines what a deployable artefact is, how a
> commit becomes a running system, and what "roll back to the previous tag" is allowed to mean.
> It deliberately creates **no tag**: an arbitrary tag minted to satisfy a gate is not a predecessor,
> it is a gate bypass.

---

## Why this exists before OL-2B…OL-2D

The absence of tags was first written up as a rollback blocker. That is the smaller half. Measured on
2026-08-31, **rollback as a reproducible operation does not exist at all**, and tags would not create
it:

| Measured fact | Consequence for rollback |
|---|---|
| `docker-compose.yml` builds the backend with `build: context: ./backend` | There is no built artefact to return to — "rollback" would mean rebuilding an old checkout against today's base image, today's PyPI index and today's apt mirror |
| `/opt/HostFlow/backend` is bind-mounted **read-write** into the running container at `/app` | The image barely matters: the code actually executing is whatever is in the working tree at restart |
| Caddy serves `/opt/HostFlow/hostflow-frontend/dist` directly (bind mount, read-only) | The live document root **is** the build output directory |
| `rebuild-frontend.sh` rsyncs into `/var/www/hostflow-frontend`, a path Caddy does not serve — its newest file is dated 2026-07-31 while the served `dist` is dated 2026-08-28, and `index.html` differs | The committed deploy script's publish step has had **no effect on what is served for a month**. The real publish is `vite build` overwriting the live root in place |
| No `emptyOutDir` override in the Vite config (default is to empty the output directory) | Every frontend build **empties the live document root** before repopulating it. There is no atomic swap and no rollback target |
| `hostflow-frontend/dist` is gitignored; no build metadata is emitted | The served bundle cannot be traced to a commit, so the currently deployed frontend is of **unknown provenance** |
| Backend exposes `version="0.5.0"` (a hand-edited literal in `main.py`) and `/healthz` returns `{"status":"ok"}` | The running system cannot answer "which commit are you?" at all |

**Therefore:** minting a tag now would label a deployment whose frontend provenance is unknown and
whose backend is a mutable working tree. The tag would be a fiction. The contract must come first.

---

## The contract

### C-1. Deployable backend artefact

A backend artefact is a **container image**, and its identity is its **image digest**.

An image qualifies only if all hold:

1. Built from a clean checkout of one commit — no uncommitted changes in the build context.
2. Application code is **inside** the image. It is not qualified by a read-write bind mount of the
   source tree at runtime.
3. Carries `org.opencontainers.image.revision` = the full commit SHA, `.version` = the release tag
   when one exists, and `.created` = build timestamp, as image labels.
4. Contains **no secret material** (see [credential exposure record](../../security/credential-exposure-and-secrets-injection.md); enforced by `backend/.dockerignore` since `2408a5a0`).
5. Is addressable later by digest — retained in a registry or an exported store, not only in the local
   daemon cache of one host.

**Current state: FAILS 1, 2, 3, 5.**

### C-2. Deployable frontend artefact

A frontend artefact is an **immutable directory or archive of built static files**, and its identity
is a **content hash over that tree** plus the commit it was built from.

It qualifies only if all hold:

1. Built from one commit with `npm ci` against the committed `package-lock.json` — never `npm install`.
2. Built **outside** the live document root. A build must never write into the directory being served.
3. Published **atomically**: materialise the new tree beside the current one and switch a symlink (or
   equivalent single-step swap). The previous tree is retained, which is what makes frontend rollback
   possible at all.
4. Emits a served build-metadata file (commit SHA, build ID, build timestamp) so provenance is
   answerable from the outside.

**Current state: FAILS 2, 3, 4** — and 1 is unverified, because the served bundle's provenance is
unknown.

### C-3. How a commit SHA reaches the deployed build

The SHA is not documented alongside the deployment; it is **carried by it**.

- Backend: build arg → image label → runtime environment variable → exposed on a read-only endpoint.
- Frontend: build-time injection → the build-metadata file published with the bundle.
- The claim "commit X is deployed" is evidenced by **querying the running system**, not by consulting
  a runbook, a chat message or a person's memory.

Until an endpoint exposes it, no deployment record may assert a commit; it may only assert what was
*intended* to be deployed, which is not evidence.

### C-4. What "previous tag" means

Release tags live in a single reserved namespace, `release/vX.Y.Z`, on the trusted base only.

"Previous tag" means: **the release tag immediately preceding the candidate in that namespace, which
was itself deployed by this procedure and has an execution record.** It is not the chronologically
previous git tag, not a tag on another branch, and not a tag that was never deployed.

A tag with no execution record is not a rollback target, because nothing establishes that the system
ever ran from it.

### C-5. Which first tag may count as a predecessor

There are zero tags, and the running deployment cannot honestly be tagged: its frontend provenance is
unknown and its backend executes a mutable working tree. Tagging it would assert a commit-to-runtime
correspondence that does not exist.

**Therefore the first predecessor is manufactured, not discovered.** The permitted sequence:

1. Choose a commit on the trusted base.
2. Build backend and frontend artefacts from it **through the OL-2B procedure**, satisfying C-1 and C-2.
3. Deploy them to the throwaway target and record an execution entry.
4. Tag that commit `release/v0.1.0`. It is a valid predecessor **because it was built and deployed by
   the procedure**, not because a tag was created.
5. The rehearsal candidate is a later commit, tagged the same way.

Explicitly forbidden: tagging the current production commit to "have a predecessor"; tagging
retroactively; tagging a commit whose artefacts were never built by the procedure.

### C-6. Rollback must not rebuild

**A rollback redeploys a previously built artefact by identity. It never re-runs a build from an old
commit.**

Rebuilding an old commit today produces a different artefact: base images, the PyPI index, the npm
registry and apt mirrors have all moved. Such a rebuild proves the commit still *compiles*, which is
not the question a rollback answers.

Enforcement requirements:

- Artefacts for at least the last **three** releases are retained and addressable by digest/hash.
- The rollback procedure names a digest or content hash, never a git ref plus a build step.
- If the artefact cannot be found, the rollback has **failed**. It does not fall back to rebuilding.

### C-7. Migration compatibility (constrains C-6)

Redeploying old code against a database migrated forward is not a rollback unless the schema still
supports that code.

- A release whose migrations are **backward-compatible** (expand-only: additive columns/tables,
  nullable or defaulted, no drops or narrowing renames) may be rolled back by artefact alone.
- A release containing a **destructive or narrowing** migration may not. It must declare itself
  irreversible, and its rollback path is restore-from-backup ([OL-5](operate-and-launch.md)), not
  redeploy.
- Every release therefore carries a **rollback class**: `artefact-reversible` or
  `restore-only`, decided from its migrations and recorded before deployment.

"Restart the old code" is not a proven rollback until the schema question is answered.

---

## OL-2 slice split

| Slice | Scope | Gate condition | Depends on |
|---|---|---|---|
| **OL-2A** | This contract; artefact identity for backend and frontend; build metadata carried by the running system | Contract recorded **and enforced** — images labelled, frontend published atomically with build metadata, provenance queryable | OL-1 |
| **OL-2B** | The real **RB-2**: clean target → running application, including migrations **and** the first-admin/bootstrap path | A non-author operator reaches a working login on a clean target from the written procedure alone | OL-2A |
| **OL-2C** | CI parity: Postgres 15 vs 16-alpine, two `alembic.ini` under a declared single source of truth, migration-only CI that never starts the app | One canonical path used by both CI and RB-2 as far as practical; every remaining difference named and justified | OL-2B |
| **OL-2D** | Rollback rehearsal on a throwaway target, with migration compatibility established per C-7 | Candidate deployed, rolled back to a C-5 predecessor, and the system proven **working** — not merely started — after rollback | OL-2A ∧ OL-2B ∧ OL-2C |

### Execution status is separate from implementation status

OL-2 may be **fully implemented by the author**. The final execution gate stays **NOT EXECUTED** until
an independent operator performs the OL-2D rehearsal, per [OL1-C1](../gates/launch-ownership-gate.md)
and the OL-1 definition of "executed". This is a normal intermediate state and does **not** block
OL-2A…OL-2D development. What it blocks is the gate's closure.

No technical workaround may substitute for the witness. Self-attested execution is not evidence.

---

## Out of scope

Zero-downtime and blue-green deployment; IaC; multi-environment promotion; registry vendor selection
beyond what C-1.5 requires; autoscaling; SLO targets.

---

## History

- 2026-08-31: Contract drafted from measurement. Recorded that rollback does not exist as a
  reproducible operation — the backend runs a bind-mounted working tree, the frontend is built in
  place over the live document root with `emptyOutDir` semantics, and the committed deploy script
  publishes to a path that has not been served since 2026-07-31. No tag created, by design: C-5
  requires the first predecessor to be built by the procedure rather than asserted retroactively.
