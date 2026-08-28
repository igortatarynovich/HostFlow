# Operate & Launch

**Status:** **QUEUED** (brief only; **not scheduled**) — second track, runs parallel to the Product Track
**Phase class:** platform
**Track:** **Launch-ops** (write-set disjoint from Product: `deploy/`, `docs/runbooks/`, infra config, tenant-lifecycle product surfaces)
**Branch (docs):** `docs/v1-blocker-briefs`
**Branch (code):** none — later slices `feat/operate-launch-olN-…`
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) (blocker 6) · [Release Readiness Gate](../gates/release-readiness-gate.md) RR3 / RR4 / RR5 / RR7 · [Acceptance suite RS-10…RS-12](../journeys/release-readiness-acceptance-suite.md) · [ADR-039 Tenant Data Lifecycle](../architecture/ADR-039-tenant-data-lifecycle.md) · [Runbook index](../../runbooks/README.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md) · [Sequential queue](sales-to-comms-sequential-queue.md)
**Estimate:** 10–14 slices (1 slice = one docs PR + one feat PR)

> v1 blocker 6: **the product can be deployed, monitored, backed up, restored, onboarded, exported, offboarded and supported by someone who did not build it.**
> Five feature blockers make HostFlow *complete*. This one makes it *sellable*: without it a paying tenant cannot be served even if every capability works.
> **Not** a production platform / SRE programme. **Not** multi-region, autoscaling, IaC, blue-green, SLO engineering. **Not** post-release steady-state operations. **Not** Billing (self-service Billing stays later).
> Opening this brief does **not** schedule it. Activation requires a queue amendment naming the Launch-ops track.

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
| `alembic upgrade heads` fails on a fresh database | [AGENTS.md](../../../AGENTS.md) § Migration caveats | Directly contradicts RC condition 4 — this is the sharpest single launch blocker |

---

## Internal ladder (Launch-ops track)

Sequential inside this track; parallel to the Product Track. One Active Launch-ops slice at a time.

```text
OL-1 Launch contract & ownership seal (docs)
  → OL-2 Deploy, migrate & rollback (executed)
  → OL-3 Production runtime defaults (queue / storage / scheduler)
  → OL-4 Operability signal (readiness, scrape, alerts, receiver)
  → OL-5 Backup & recovery drill
  → OL-6 Tenant lifecycle as product (create → import → export → erase)
  → OL-7 Support & incident path
  → Operate & Launch program close (outcome + release delta)
```

| # | Slice | Machine id | Named gate (PASS =) | Depends on | Estimate |
|---|-------|------------|---------------------|------------|----------|
| **OL-1** | Launch contract & ownership seal | `ol-contract` | **Launch Ownership Gate** — production target defined; RR3 / RR4 / RR7 owners named; required runbook set enumerated in [`docs/runbooks/README.md`](../../runbooks/README.md) with owner and status; “executed” defined as a dated record; [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md) accepted | queue amendment opening the Launch-ops track | 1 slice (docs) |
| **OL-2** | Deploy, migrate & rollback | `ol-deploy` | **Deploy & Rollback Gate** — a written procedure takes a tagged commit to a non-dev target, applies migrations to a **freshly created** DB with no manual repair, serves a reproducibly built frontend, and rolls back to the previous tag; executed once by someone other than its author | OL-1 Gate | 2–3 slices |
| **OL-3** | Production runtime defaults | `ol-runtime` | **Production Runtime Defaults Gate** — durable queue and non-local object storage are the documented production configuration with a running worker; scheduled work has exactly one owner process (no double-send); scripts that require cron have a scheduler manifest | OL-2 Gate | 2 slices |
| **OL-4** | Operability signal | `ol-signal` | **Operability Signal Gate** — readiness endpoint answers for Postgres / Redis / storage; a scrape config and a minimal alert set exist as loaded configuration; an alert reaches a named human; the minimal set is justified per metric | OL-3 Gate | 1–2 slices |
| **OL-5** | Backup & recovery drill | `ol-recovery` | **Recovery Drill Gate** (proves RS-12) — backup runs unattended; a drill restores database **and** document storage onto a clean target from backup only, with observed RPO / RTO recorded and dated | OL-3 Gate | 2 slices |
| **OL-6** | Tenant lifecycle as product | `ol-tenant` | **Tenant Lifecycle Gate** (proves RS-10, RS-11) — an operator creates a tenant, loads an existing customer base, produces a complete export, and erases the tenant, all through product surfaces per [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md); no `psql`, no purge script | OL-1 Gate ∧ ADR-039 accepted | 2–3 slices |
| **OL-7** | Support & incident path | `ol-support` | **Incident Path Gate** — severity levels, on-call owner, escalation, rollback window and customer-communication owner exist as a runbook; one rehearsed incident recorded end to end | OL-4 Gate ∧ OL-5 Gate | 1 slice |

---

## OL-1 — Launch contract & ownership seal (queued, docs only)

Answers what nothing currently answers:

1. **What is the production target for v1?** One target, named (single host / single compose stack is acceptable for v1 — this brief does not require orchestration).
2. **Who owns RR3, RR4, RR7?** A named person per question; the [Release Readiness Gate](../gates/release-readiness-gate.md) cannot be answered by a role that does not exist.
3. **Which runbooks must exist**, with owner and current status — recorded in [`docs/runbooks/README.md`](../../runbooks/README.md).
4. **What “executed” means:** a dated record naming the operator, the target, the build, and the observed result. A runbook without such a record does not count (gate evidence bar).
5. **Accepts [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md)** so OL-6 has a contract instead of inventing one per module.

Out: writing the runbooks themselves (OL-2…OL-7 own them); choosing hosting vendors; SLO targets.

## OL-2 — Deploy, migrate & rollback (queued)

The blocking sub-problem is migrations: per `AGENTS.md`, `alembic upgrade heads` does **not** apply cleanly to a fresh database, and the documented workaround is a hand-ordered sequence with a manual `CREATE TYPE` and a `stamp`. RC condition 4 forbids exactly that. This slice either fixes the migration graph or replaces it with a documented, automated bootstrap — an insider-only sequence is a STOP.

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
**Depends on:** a queue amendment opening the track; OL-6 additionally on ADR-039 acceptance
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
