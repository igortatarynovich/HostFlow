# Operate & Launch

**Status:** **ACTIVE** — Launch-ops track opened 2026-08-31; **OL-1 delivered** ([Launch Ownership Gate](../gates/launch-ownership-gate.md) `PASS_WITH_CONSTRAINTS`). **Next slice: OL-2** Deploy, migrate & rollback — named, **not started**: invariant 6 of the [queue](sales-to-comms-sequential-queue.md) forbids starting a slice in the same PR that closes its predecessor. Runs parallel to the Product Track
**Phase class:** platform
**Track:** **Launch-ops** (write-set disjoint from Product: `deploy/`, `docs/runbooks/`, infra config, tenant-lifecycle product surfaces)
**Branch (docs):** `docs/v1-blocker-briefs`
**Branch (code):** `feat/operate-launch-ol2a-artefact-identity` (OL-2A executable; live stack unchanged)
**Production target (v1, decided OL-1):** one dedicated host, one compose stack. No staging environment, so OL-2's rollback rehearsal and OL-5's restore drill build a throwaway target — see [OL1-C2](../gates/launch-ownership-gate.md)
**RR3 / RR4 / RR7 owner (decided OL-1):** `igortatarynovich` for all three; single-person ownership is a named residual carried to OL-7 ([OL1-C1](../gates/launch-ownership-gate.md))
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) (blocker 6) · [Release Readiness Gate](../gates/release-readiness-gate.md) RR3 / RR4 / RR5 / RR7 · [Acceptance suite RS-10…RS-12](../journeys/release-readiness-acceptance-suite.md) · [ADR-039 Tenant Data Lifecycle](../architecture/ADR-039-tenant-data-lifecycle.md) · [Runbook index](../../runbooks/README.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md) · [Sequential queue](sales-to-comms-sequential-queue.md)
**Estimate:** 10–14 slices (1 slice = one docs PR + one feat PR)

> v1 blocker 6: **the product can be deployed, monitored, backed up, restored, onboarded, exported, offboarded and supported by someone who did not build it.**
> Five feature blockers make HostFlow *complete*. This one makes it *sellable*: without it a paying tenant cannot be served even if every capability works.
> **Not** a production platform / SRE programme. **Not** multi-region, autoscaling, IaC, blue-green, SLO engineering. **Not** post-release steady-state operations. **Not** Billing (self-service Billing stays later).
> Opened by the [2026-08-31 queue amendment](sales-to-comms-sequential-queue.md) § 8. OL-1 is closed; OL-2 is the active slice.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
HostFlow today is operable **only by its builder**. There is no deploy procedure beyond a developer-oriented `docker compose` plus a frontend rebuild note, no rollback procedure at all, no backup or restore of any kind, no alerting on a live outage, no way to delete a tenant except a SQL purge script, no way to export a tenant’s or a person’s data, and no defined path from “a customer says it broke” to “the customer has been told what happens next”. Critical background work (reminders, SLA escalation, document expiry) runs inside the API process by default, and uploaded documents land on a local disk by default. Every one of these is a single point at which the first paying customer is lost, and none of them is owned by a v1 slice.

**Completion proof (named consumer):**
**RS-10, RS-11 and RS-12 in the [acceptance suite](../journeys/release-readiness-acceptance-suite.md)**, executed by a non-developer on the Release Candidate: a tenant is created and loaded with a customer’s existing data, its data is fully exported and then erased, and the service is destroyed and recovered from backup with observed RPO/RTO recorded. Plus the RC definition itself: the RC exists only when a tagged commit is deployed to a non-developer target by the same procedure production will use, with migrations applied to a **freshly created** database without manual repair.

**False close (reject):** a runbook that has never been executed; a restore drill on a database that was never really lost; “deploy” = `git pull` plus a manual `npm run build` on the server; a tenant deleted with `psql`; alert rules written in a doc but not loaded by anything; naming an on-call owner without a rollback window; declaring RR3/RR4/RR7 answered by intent.

---

## Starting point (measured, not assumed)

Evidence collected 2026-08-28 across `docker-compose.yml`, `deploy/`, `.github/workflows/`, `backend/app`, `hostflow-frontend/src`, `docs/`.

### What exists and is usable

| Capability | Where | Note |
|------------|-------|------|
| Container stack | `docker-compose.yml`, `backend/Dockerfile` | Postgres 16, Redis 7, backend uvicorn; ARQ worker and MinIO behind compose profiles |
| Reverse proxy / SPA serving | `Caddyfile`, `deploy/nginx/hostflow.conf`, `deploy/caddy.Dockerfile` | Three serving paths exist (Caddy, nginx, FastAPI static mount) |
| Frontend deploy note | `docs/FRONTEND_DEPLOY.md` | Executable; server-specific |
| Frontend deploy **script** | `rebuild-frontend.sh` (measured 2026-08-31) | `npm run build` in the checkout → `rsync -a --delete` into `/var/www/hostflow-frontend/` → `docker-compose restart caddy`. This is the § False close ("`git pull` plus a manual `npm run build` on the server") existing as a committed script. `hostflow-frontend/dist` is gitignored, so the served artefact is not traceable to a commit |
| Troubleshooting note | `deploy/TROUBLESHOOTING.md` | Executable; assumes `hostflow.cc` host knowledge |
| Metrics | `/metrics` + `backend/app/observability/metrics.py` | Real custom metrics (overdue documents, reminders, leads) |
| Structured logs + request ids | `backend/app/core/observability.py`, `main.py` | `LOG_FORMAT=json`, `X-Request-ID`, security correlation |
| Optional error tracking | `SENTRY_DSN` (backend), `VITE_SENTRY_DSN` (frontend) | Off by default |
| Security events + detection | `backend/app/security/canonical_emit.py`, `detection_engine.py` | Emitted as log lines; optional webhook |
| Durable queue **capability** | `backend/app/core/queue.py`, `arq_worker.py`, [job_queue.md](../architecture/job_queue.md) | ARQ exists; not the default |
| Object storage **capability** | `backend/app/core/object_storage.py`, [object_storage.md](../architecture/object_storage.md) | S3/MinIO exists; not the default |
| Alembic preflight | `scripts/deploy/alembic_preflight.py` | Graph check only; explicitly does not upgrade |
| Tenant provisioning | `POST /api/v1/platform/tenants` + `/app/settings/tenants`; `POST /api/v1/auth/register` | Tenant + license + first admin exist as product |
| Onboarding wizard | `backend/app/api/v1/onboarding.py` | 5 steps to first lead; other setup is per-settings-page |
| Isolation tests | `backend/tests/api/test_tenant_isolation.py`, `backend/tests/security/test_tenant_rls_session_guard.py` | Real negative tests, incl. fail-closed session guard |
| Superadmin audit | `platform/tenants.py`, `backend/app/db/deps.py` | Impersonation + elevated DB bind emit security events |
| Incident triage (security only) | `docs/security/security-review-checklist.md` §IR, `docs/security/detection-runbooks.md` | Data leak / credential / malware triage exist |

### What is absent (searched, not found)

| Missing | Search anchor |
|---------|---------------|
| Any deploy pipeline (SSH / registry push / kubectl) | all 8 workflows in `.github/workflows/` are test / lint / gate only |
| Rollback procedure | `rollback` across `*.md`, `scripts/`, `deploy/` — only DB transaction rollback and the gate’s own requirement |
| **Any git tag at all** (measured 2026-08-31: `git tag` returns 0) | OL-2's gate requires rolling back "to the previous tag" and RC condition 1 requires tagging the RC. There is no predecessor tag, so OL-2 must create a baseline tag **before** a rollback rehearsal is possible at all |
| A deployable artefact | `docker-compose.yml` builds the backend with `build: context: ./backend` — the image is built from the checkout on the host, not pulled from a registry, so there is no built artefact to roll back *to* |
| Backup / restore of Postgres | `pg_dump`, `pgbackrest`, `wal-g` — none |
| Deep readiness endpoint | `/readyz`, `/livez` absent; `/healthz` returns `ok` without touching Postgres or Redis |
| Scrape config, dashboards, alert rules | `prometheus.yml`, `grafana`, `alertmanager` — none in repo; [observability.md](../platform/observability.md) §3 is aspirational |
| `docs/ops/**`, `docs/runbooks/**` | 0 files (one niche runbook lives at `docs/specs/runbooks/phase-2-1-drop-runbook.md`) |
| Tenant delete | no `DELETE /platform/tenants`; `TenantStatus` has `active / suspended / trial` only; offboarding = `scripts/purge_test_tenants.sql` |
| Tenant-wide export | exports are per-entity or client-side CSV; no aggregate |
| Per-person (DSAR) export / erasure | `dsar`, `subject access`, `anonymiz`, `pseudonymiz` — none; the FAQ nevertheless promises anonymisation (`faqCatalog.ts`) |
| Bulk import of a customer’s existing base | only `services/imports/leads.py` + HR org-unit JSON; no candidate / client / vacancy / employee / document importer |
| DPA, subprocessor list | `DPA`, `data processing agreement`, `subprocessor` in `docs/` — none |
| On-call, severity matrix, status page, support intake | none in `docs/` |
| Cron / systemd units for the scripts that say “intended for cron” | `dispatch_hr_operational_alerts.py`, `run_zus_workspace_monthly_cycle.py` have no scheduler manifest |

### Defaults that are wrong for a paying tenant

| Default | Where | Consequence |
|---------|-------|-------------|
| `JOB_QUEUE_BACKEND=inprocess` | `backend/app/core/settings.py` | Reminders / SLA / expiry work dies with the API process; ARQ worker is profile-gated and the backend service does not request it |
| Communications scheduler inside the API process | `main.py` lifespan + `services/communications_scheduler.py` | [job_queue.md](../architecture/job_queue.md) itself warns that a second replica double-sends |
| `OBJECT_STORAGE_BACKEND=fs` | `backend/app/core/settings.py` | Customer documents on a container-local disk; loss on host failure, no horizontal scale |
| Migrations not applied by the container entrypoint | `backend/Dockerfile` CMD is uvicorn only | Deploy correctness depends on someone remembering `alembic upgrade` |
| ~~`alembic upgrade heads` fails on a fresh database~~ — **withdrawn 2026-08-31, see § Correction below** | [AGENTS.md](../../../AGENTS.md) § Migration caveats | Measured false. The surviving defect is one layer down: the migrated schema rejects the bootstrap admin, and the seed swallows the error |
| ~~A fresh instance starts **healthy with no admin user**~~ — **closed 2026-08-31, see History** | `backend/app/auth/ensure_seed.py`; `202608310001_bootstrap_admin_schema` | Measured true, then fixed in-graph. `superadmin` is an ADR-036 persisted role; `preferences` default is `'{}'`. Seed no longer swallows the insert. Author clean-pass is **not** gate execution |
| The trusted-base checkout **is** the production runtime | `docker inspect hostflow-backend-1`; measured 2026-08-31 | `/opt/HostFlow/backend` is bind-mounted read-write at `/app` in the running container and Caddy serves `/opt/HostFlow/hostflow-frontend/dist`. "Deploy" today is editing the working tree of the live host; a branch switch changes production |

---

## Correction — the fresh-database migration blocker does not exist (measured 2026-08-31)

This brief opened by calling `alembic upgrade heads` on a fresh database "the sharpest single launch blocker". That was inherited from [`AGENTS.md`](../../../AGENTS.md) § Migration caveats and never measured. It has now been measured, and it is false.

**Method.** Two disposable Postgres 16 containers, each a genuinely empty database (0 public tables), on the current trusted base `f03a4dbd`. Alembic run under a scrubbed environment (`env -i`) with all three URL variables pinned to the throwaway port, so no fallback to the live database was possible. The production stack was not touched.

| Run | Command | Result |
|---|---|---|
| 1 | `alembic upgrade heads` | exit 0 · 299 revisions · head `202608250002_merge_e5_drop_and_adr036_heads` · 236 tables · 0 errors |
| 2 | `alembic upgrade head` | exit 0 · same head · 236 tables |

**Why the old caveats were wrong.** The `alembic_version` column does not need widening by hand — [`20260113_widen_alembic_version.py`](../../../backend/alembic/versions/20260113_widen_alembic_version.py) does it inside the graph before any of the 109 over-length revision ids is recorded (verified: the fresh database ends with `character varying(255)` holding a 43-character id). The parallel branch tips do not need hand-ordering — there is one head, 25 merge points, and alembic's own ordering suffices. `202605200001` does not need stamping over — it applies, and `202511130001` drops its objects as designed.

**What survives, and is now OL-2's actual migration problem.** The schema the migrations produce cannot accept the admin the bootstrap writes. Reproduced directly against the fresh database:

```
ERROR:  invalid input value for enum role: "superadmin"
ERROR:  null value in column "preferences" of relation "users" violates not-null constraint
```

`ensure_seed.py` inserts `role='superadmin'` and omits `preferences`; no migration adds `superadmin` to the enum, and `preferences` is `NOT NULL` with no server default. The seed catches the exception and startup continues, so the failure is silent.

**CI has been proving this all along (added on re-check, same day).** Three workflows already build a fresh database and migrate it: `backend-ci.yml` (job `alembic`), `backend-regression.yml` and `hr-e2e-api.yml` each start a `postgres:15` service and run `alembic upgrade head`. On run [#326](https://github.com/igortatarynovich/HostFlow/actions/runs/33169406846) — a push to the trusted base — the `alembic` job is **green**. So the caveat in `AGENTS.md` was not merely unverified; the repository's own CI had been contradicting it on every push, and nobody read it that way.

**Release consequence — corrected.** RC condition 4 reads "migrations apply to a freshly created database **by the documented procedure**, without manual repair steps". The migration half is proven, continuously. The half that fails is **"by the documented procedure"**: RB-2 does not exist, so there is no procedure for the condition to be satisfied *by*. Three gaps sit behind that, all OL-2's:

- CI proves it on `postgres:15`; production runs `postgres:16-alpine` (this measurement used 16, so both are now covered in fact — but not by a procedure).
- CI drives `backend/alembic.ini` via `working-directory: backend`, while [`AGENTS.md`](../../../AGENTS.md) § Alembic Layout declares the repo-root `alembic.ini` the single source of truth. Two files, both resolving to `backend/alembic`; OL-2 should pick one.
- CI stops at migrations and never starts the application, so the bootstrap defect above is invisible to it.

This also removes the stated obstacle to running the isolation suite under the restricted role in CI ([RR5](../gates/release-readiness-gate.md), [TI-5](tenant-isolation-enforcement.md)): the database CI "cannot build" is one it already builds.

**Not claimed here.** That a fresh instance is usable — it is not, per the bootstrap defect above. That backend-ci is green — it is **red on the trusted base** since 2026-08-28, on the DR1 Runtime Gate, which is unrelated to migrations and not this brief's. That any runbook exists — RB-1…RB-10 remain ten of ten MISSING.

---

## Internal ladder (Launch-ops track)

Sequential inside this track; parallel to the Product Track. One Active Launch-ops slice at a time.

```text
OL-1 Launch contract & ownership seal (docs)
  → OL-2 Deploy, migrate & rollback (executed)
       OL-2A deploy contract & artefact identity
       OL-2B documented deploy + bootstrap (RB-2)
       OL-2C CI parity
       OL-2D rollback rehearsal (needs an independent operator)
  → OL-3 Production runtime defaults (queue / storage / scheduler)
  → OL-4 Operability signal (readiness, scrape, alerts, receiver)
  → OL-5 Backup & recovery drill
  → OL-6 Tenant lifecycle as product (create → import → export → erase)
  → OL-7 Support & incident path
  → Operate & Launch program close (outcome + release delta)
```

| # | Slice | Machine id | Named gate (PASS =) | Depends on | Estimate |
|---|-------|------------|---------------------|------------|----------|
| **OL-1** ✅ | Launch contract & ownership seal | `ol-contract` | **[Launch Ownership Gate](../gates/launch-ownership-gate.md) — `PASS_WITH_CONSTRAINTS` 2026-08-31.** production target defined; RR3 / RR4 / RR7 owners named; required runbook set enumerated in [`docs/runbooks/README.md`](../../runbooks/README.md) with owner and status; “executed” defined as a dated record; [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md) accepted | queue amendment opening the Launch-ops track | 1 slice (docs) |
| **OL-2** | Deploy, migrate & rollback — **split into [OL-2A…OL-2D](operate-launch-ol2-deploy-contract.md)** | `ol-deploy` | **Deploy & Rollback Gate** — a written procedure takes a tagged commit to a non-dev target, applies migrations to a **freshly created** DB with no manual repair, serves a reproducibly built frontend, and rolls back to the previous tag; executed once by someone other than its author. **Execution status is tracked separately from implementation:** the gate stays `NOT EXECUTED` until an independent operator runs the OL-2D rehearsal, which does not block OL-2A…OL-2D development | OL-1 Gate | 4 slices (A/B/C/D) |
| **OL-3** | Production runtime defaults | `ol-runtime` | **Production Runtime Defaults Gate** — durable queue and non-local object storage are the documented production configuration with a running worker; scheduled work has exactly one owner process (no double-send); scripts that require cron have a scheduler manifest | OL-2 Gate | 2 slices |
| **OL-4** | Operability signal | `ol-signal` | **Operability Signal Gate** — readiness endpoint answers for Postgres / Redis / storage; a scrape config and a minimal alert set exist as loaded configuration; an alert reaches a named human; the minimal set is justified per metric | OL-3 Gate | 1–2 slices |
| **OL-5** | Backup & recovery drill | `ol-recovery` | **Recovery Drill Gate** (proves RS-12) — backup runs unattended; a drill restores database **and** document storage onto a clean target from backup only, with observed RPO / RTO recorded and dated | OL-3 Gate | 2 slices |
| **OL-6** | Tenant lifecycle as product | `ol-tenant` | **Tenant Lifecycle Gate** (proves RS-10, RS-11) — an operator creates a tenant, loads an existing customer base, produces a complete export, and erases the tenant, all through product surfaces per [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md); no `psql`, no purge script | OL-1 Gate ∧ ADR-039 accepted | 2–3 slices |
| **OL-7** | Support & incident path | `ol-support` | **Incident Path Gate** — severity levels, on-call owner, escalation, rollback window and customer-communication owner exist as a runbook; one rehearsed incident recorded end to end | OL-4 Gate ∧ OL-5 Gate | 1 slice |

---

## OL-1 — Launch contract & ownership seal ✅ (delivered 2026-08-31, docs only)

Answers what nothing currently answers:

1. **What is the production target for v1?** One target, named (single host / single compose stack is acceptable for v1 — this brief does not require orchestration).
2. **Who owns RR3, RR4, RR7?** A named person per question; the [Release Readiness Gate](../gates/release-readiness-gate.md) cannot be answered by a role that does not exist.
3. **Which runbooks must exist**, with owner and current status — recorded in [`docs/runbooks/README.md`](../../runbooks/README.md).
4. **What “executed” means:** a dated record naming the operator, the target, the build, and the observed result. A runbook without such a record does not count (gate evidence bar).
5. **Accepts [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md)** so OL-6 has a contract instead of inventing one per module.

Out: writing the runbooks themselves (OL-2…OL-7 own them); choosing hosting vendors; SLO targets.

## OL-2 — Deploy, migrate & rollback (**next** — named, not started)

**The premise this slice was framed around has been measured false — see § Correction (2026-08-31).** The migration graph applies to a freshly created database in one command. What remains for OL-2 is smaller in one place and larger in another.

Smaller: there is no migration graph to repair, and no CI proof to build either — three workflows already migrate a fresh `postgres:15` and the `alembic` job is green. What is left of RC condition 4 is the words "by the documented procedure": RB-2 does not exist, CI's Postgres major version does not match production's, and CI stops before the application starts.

Larger: the fresh-database defect moved downstream and got quieter. A freshly migrated instance starts healthy with **no admin user**, because the bootstrap insert violates the `role` enum and the `preferences` NOT NULL constraint and the seed swallows both. A deploy runbook that checks liveness would not catch it. And because `auth_seed_enabled()` is off by default, a production target never runs that seed at all, so this slice must name the first-admin path explicitly rather than inherit one.

Also inherited: "deploy" currently means editing the working tree of the live host (§ Starting point). The procedure this slice writes has to replace that, not document it.

**Split into four self-consistent slices, with the release semantics fixed first — [OL-2A…OL-2D](operate-launch-ol2-deploy-contract.md).** Measurement on 2026-08-31 showed the missing tags were the smaller half of the problem: **rollback does not exist as a reproducible operation**, and tagging would not create it. The backend image is built from the working tree and then overridden by a read-write bind mount of that same tree; Caddy serves the frontend build output directory itself, so `vite build` empties and rewrites the live document root in place; and `rebuild-frontend.sh` publishes to `/var/www/hostflow-frontend`, which Caddy does not serve and whose newest file predates the served bundle by a month. No tag is created by OL-2A, deliberately: the running deployment cannot be honestly tagged, because the served frontend's provenance is unknown and the backend executes a mutable tree. After `cdfb8697` the **release path** can produce a labelled image and a hashed frontend tree; the live compose still does not use that path.

**Entry condition — corrected 2026-08-31.** The Deploy & Rollback Gate requires execution by someone other than the author, and OL-1 recorded a single holder for RR3 / RR4 / RR7. This was first written as a condition that must be satisfied *before* the slice starts. That is wrong and would stall the work for a staffing reason: **implementation and execution are separate statuses.** OL-2A…OL-2D may be implemented in full by the author; the gate simply stays `NOT EXECUTED` until an independent operator performs the OL-2D rehearsal. That is a normal intermediate state. No technical substitute for the witness is permitted — self-attested execution is not evidence. OL-7 still owns the escalation half of OL1-C1.

Out: zero-downtime, blue-green, IaC, multi-environment promotion.

## OL-3 — Production runtime defaults (queued)

Flip the two defaults that lose customer data and customer promises (`inprocess` queue, `fs` storage), and give the communications scheduler a single owner. Out: rewriting the scheduler into the queue (that is the [job_queue.md](../architecture/job_queue.md) migration, larger than v1), autoscaling.

## OL-4 — Operability signal (queued)

Minimum: is it up (deep readiness), is it failing (error rate / 5xx), is it falling behind (queue lag / scheduler heartbeat), is it out of room (disk / DB connections), does an alert reach a human. Out: dashboards as a product, tracing, SLO burn-rate alerting.

## OL-5 — Backup & recovery drill (queued)

Restore must cover **both** Postgres and document storage — with `fs` storage a database-only backup silently loses every uploaded document. Out: cross-region replication, PITR tooling choice beyond what the drill needs.

## OL-6 — Tenant lifecycle as product (queued)

Four operator verbs: create, load, export, erase. Notable starting facts: erasure today is soft-delete (`deleted_at`) that leaves documents, communications and audit rows in place; the product FAQ promises anonymisation that no backend code implements; and a customer’s existing candidate base cannot be imported at all. Out: self-service billing, migration services per customer, DSAR workflow automation beyond the export/erase primitives.

## OL-7 — Support & incident path (queued)

Out: 24/7 rotation, paid support tiers, status-page product.

---

## Ownership card (Rule 3)

| Field | Value |
|-------|-------|
| **Domain** | Operate & Launch (release operations for v1) |
| **Owner** | Operational lead (RR4, RR7) + Engineering lead (RR3, RR6); Security owner co-signs RR5 items touching erasure/export |
| **Source of truth** | This brief for scope; [`docs/runbooks/`](../../runbooks/README.md) for procedures; [Release Readiness Gate](../gates/release-readiness-gate.md) for the release decision |
| **Consumers** | Release Readiness Gate (RR3/RR4/RR7), acceptance suite RS-10…RS-12, first paying tenant |
| **Delivery contract** | Executed runbooks with dated records; product surfaces for tenant lifecycle per ADR-039 |
| **Versioning** | Runbooks are versioned documents; each execution record is append-only |
| **Override policy** | None — residuals only via the gate’s § Named residuals with owner, expiry and customer-visible impact |
| **Enforcement** | Gate entry conditions EC-3 / EC-5; RC definition; CI repo-health |

---

## Program close = two results

| Field | Meaning |
|-------|---------|
| **Program outcome** | The service can be deployed, rolled back, observed, recovered and supported from written procedures, and a tenant’s whole lifecycle is an operator action |
| **Release delta** | RR3, RR4, RR7 become answerable with evidence; RS-10…RS-12 become executable; the RC definition becomes satisfiable. The five feature blockers remain **OPEN** unless separately closed. HostFlow v1 is not release-ready until the [Release Readiness Gate](../gates/release-readiness-gate.md) passes |

---

## Queue position

**Track:** Launch-ops — parallel to Product by explicit decision (write-set disjoint: no Product slice edits `deploy/`, `docs/runbooks/`, infra defaults; OL-6 is the one slice that touches product code and must not collide with an Active Product slice in the same module)
**Depends on:** ~~a queue amendment opening the track~~ (done 2026-08-31); OL-6 additionally on ADR-039 acceptance (**Accepted** 2026-08-31 by OL-1)
**Does not:** consume a Product slot; unlock Billing / AI / OCR; authorise an SRE programme; make this gate a substitute for the [Release Readiness Gate](../gates/release-readiness-gate.md)

---

## Refs

- [Release Readiness Gate](../gates/release-readiness-gate.md) — RR3 / RR4 / RR5 / RR7 and the RC definition this program must make satisfiable
- [Acceptance suite](../journeys/release-readiness-acceptance-suite.md) — RS-10 onboarding, RS-11 export/erasure, RS-12 recovery drill
- [ADR-039 Tenant Data Lifecycle](../architecture/ADR-039-tenant-data-lifecycle.md) — ownership and contract for provisioning / import / export / erasure / retention
- [Runbook index](../../runbooks/README.md) — required runbook set with owner and status
- [job_queue.md](../architecture/job_queue.md) · [object_storage.md](../architecture/object_storage.md) — the two production defaults OL-3 must flip
- [observability.md](../platform/observability.md) · [prometheus_integration.md](../platform/prometheus_integration.md) — metric catalog and scrape plan OL-4 must make real
- [crm-production-readiness-ssot.md](../../crm-production-readiness-ssot.md) — F7 manual scenario run-log (operational tracker, not the release authority)

---

## History

- 2026-08-31 (later, OL-2B first-admin): **Bootstrap admin schema closed as implementation, not as gate execution.** `superadmin` is an ADR-036 persisted trust role; `users.preferences` is a required empty object. Fresh Postgres 16 rejected both until `202608310001_bootstrap_admin_schema`. Clean throwaway pass after that commit: empty volume → migrate to that head → seed created `admin@hostflow.dev` → login 200. The throwaway composite `11f1c845` was evidence only; the first baseline must be rebuilt from a later trusted-base HEAD. OL-2B remains **PASS_IMPLEMENTATION / NOT EXECUTED** — author is not the witness.
- 2026-08-31 (later, OL-2A executable): release-path artefact identity landed on `feat/operate-launch-ol2a-artefact-identity` — OCI-labelled backend image, `GET /build`, frontend `build.json` + content-hash atomic publish, throwaway `deploy/compose.release.yml` with no source bind mounts. **Live stack unchanged.** Contract C-1…C-3 hold on that path only; C-5 first predecessor and C-6 retained store are still open. No tag created.
- 2026-08-31 (later, correction): **The fresh-database migration blocker was measured and does not exist** — see § Correction. `alembic upgrade heads` applies to an empty database in one command, twice, on `f03a4dbd`; the three manual steps in [`AGENTS.md`](../../../AGENTS.md) § Migration caveats were obsolete, one of them because the repair already lives in the graph. This retires the claim that OL-2 owns "the sharpest single launch blocker" and that RC condition 4 is unsatisfiable. On re-check the same day the framing was corrected once more: CI **already** migrates a fresh `postgres:15` in three workflows and the `alembic` job is green, so the condition's migration half is proven continuously and what fails is the phrase "by the documented procedure" — RB-2 does not exist. Two defects were found in its place and are OL-2's: a freshly migrated instance starts healthy with **no admin user** (the bootstrap insert violates the `role` enum and the `preferences` NOT NULL constraint, and the seed swallows the error), and "deploy" today means editing the working tree of the live host, which bind-mounts read-write into the running container. An entry condition was added to OL-2 for the execution-witness half of [OL1-C1](../gates/launch-ownership-gate.md), since its gate requires an operator who is not the author. Measured on the same re-check and recorded in § Starting point: the repository has **zero git tags**, so OL-2's "roll back to the previous tag" has no anchor until it creates a baseline one; the backend image is built from the checkout rather than pulled, so there is no artefact to roll back to; and `rebuild-frontend.sh` implements the § False close as a committed script.
- 2026-08-31: **Track opened; OL-1 delivered** — [Launch Ownership Gate](../gates/launch-ownership-gate.md) `PASS_WITH_CONSTRAINTS`. Production target decided (one dedicated host, one compose stack), RR3 / RR4 / RR7 given a named holder, the RB-1…RB-10 set sealed at ten of ten MISSING, "executed" defined as a dated record naming operator / target / build / result with the operator not being the author, and [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md) accepted. Two residuals recorded rather than smoothed over: one person holds all three release questions, so RR7's escalation step has no second party (carried to OL-7); and the single-host target means OL-2's rollback rehearsal and OL-5's restore drill must build a throwaway target instead of using production. Successor **OL-2**, which owns the sharpest launch blocker in § Starting point — `alembic upgrade heads` failing on a fresh database — and therefore also gates the CI half of [tenant isolation](tenant-isolation-enforcement.md).
- 2026-08-28: Brief opened as v1 blocker 6 with the measured starting point, the OL-1…OL-7 ladder and named gates. Queued, not scheduled.
