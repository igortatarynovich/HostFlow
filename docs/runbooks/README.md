# Runbooks — index

**Status:** L3 IMPLEMENTATION CONTEXT (procedures) · index is **normative for the required set**
**Date:** 2026-08-28
**Owner:** Operational lead (procedure set) + Engineering lead (deploy / recovery procedures) — both roles held by **igortatarynovich**, named by the [Launch Ownership Gate](../specs/gates/launch-ownership-gate.md) (OL-1)
**Parents:** [Operate & Launch](../specs/tasks/operate-and-launch.md) (v1 blocker 6) · [Release Readiness Gate](../specs/gates/release-readiness-gate.md) RR3 / RR4 / RR7 · [Documentation rules](../governance/documentation-rules.md) §2.1 (`docs/runbooks/<slug>.md`) · [Hierarchy of Truth](../governance/hierarchy-of-truth.md)

> A runbook is a procedure a person who did not build the system can follow to a known outcome.
> This index exists so that **missing** procedures are countable instead of assumed. A row marked MISSING is a launch gap, not a TODO.
> **Executed** means a dated record exists naming operator, target, build and observed result. A runbook that has never been executed does not satisfy the [gate’s evidence bar](../specs/gates/release-readiness-gate.md) § Evidence bar.

---

## Required set for v1

| # | Runbook | Answers | Owner | Written by | Status |
|---|---------|---------|-------|------------|--------|
| **RB-1** | Deploy a release build | RR3 | igortatarynovich | [OL-2](../specs/tasks/operate-and-launch.md) · [OL-2A](../specs/tasks/operate-launch-ol2-deploy-contract.md) | **DRAFT / NOT EXECUTED** — [rb-1-deploy-release-build.md](rb-1-deploy-release-build.md). Load retained artefacts, `compose.release.yml` project `hostflow-release`, host-side Alembic, then `/healthz` + `/build` + login. Author walks do not count |
| **RB-2** | Apply migrations to a fresh and to an existing database | RR3, RC condition 4 | igortatarynovich | [OL-2](../specs/tasks/operate-and-launch.md) · [OL-2C](../specs/tasks/operate-launch-ol2c-ci-parity.md) | **DRAFT / NOT EXECUTED** — [rb-2-migrate-and-bootstrap.md](rb-2-migrate-and-bootstrap.md). Path is `release-proof.sh` (PG16, repo-root Alembic, `/healthz` + `/build` + login) then retain-by-digest. Author walks do not count |
| **RB-3** | Roll back a release | RR3, RR7 | igortatarynovich | [OL-2](../specs/tasks/operate-and-launch.md) · [OL-2D](../specs/tasks/operate-launch-ol2d-predecessor.md) | **MISSING** — **DEFERRED_BY_INITIAL_BASELINE / NOT EXECUTED**. Expand-only rule: rollback of `202608310001_bootstrap_admin_schema` redeploys retained artefacts and **does not** `alembic downgrade` |
| **RB-4** | Start / verify background processing (queue worker, scheduler) | RR3 | igortatarynovich | [OL-3](../specs/tasks/operate-and-launch.md) | **MISSING** — [job_queue.md](../specs/architecture/job_queue.md) describes the model, not the operation |
| **RB-5** | Monitor and respond to alerts | RR3, RR7 | igortatarynovich | [OL-4](../specs/tasks/operate-and-launch.md) | **MISSING** — [observability.md](../specs/platform/observability.md) §3 names alerts that nothing loads |
| **RB-6** | Back up database and document storage | RR3 | igortatarynovich | [OL-5](../specs/tasks/operate-and-launch.md) | **MISSING** — no backup tooling in the repo |
| **RB-7** | Restore from backup (recovery drill) | RR3, RS-12 | igortatarynovich | [OL-5](../specs/tasks/operate-and-launch.md) | **MISSING** — drill required by [RS-12](../specs/journeys/release-readiness-acceptance-suite.md) |
| **RB-8** | Onboard a tenant (create, configure, load data) | RR4, RS-10 | igortatarynovich | [OL-6](../specs/tasks/operate-and-launch.md) | **MISSING** — provisioning API/UI exists; procedure does not |
| **RB-9** | Export and erase a tenant’s data | RR4, RR5, RS-11 | igortatarynovich — Security co-sign required by [ADR-039](../specs/architecture/ADR-039-tenant-data-lifecycle.md) and held by the same person, so the co-sign adds no second pair of eyes ([OL1-C1](../specs/gates/launch-ownership-gate.md)) | [OL-6](../specs/tasks/operate-and-launch.md) | **MISSING** — capability itself absent; contract in [ADR-039](../specs/architecture/ADR-039-tenant-data-lifecycle.md) |
| **RB-10** | Incident response: diagnose → escalate → mitigate → roll back → communicate | RR7 | igortatarynovich | [OL-7](../specs/tasks/operate-and-launch.md) | **MISSING** for service incidents — security incidents are covered (see below) |

Ten required procedures. RB-1 and RB-2 are written and **NOT EXECUTED**. The other eight are still MISSING. That count is the honest measure of operational readiness today.

---

## Existing procedures (not part of the required v1 set, kept as-is)

| Procedure | Path | Scope |
|-----------|------|-------|
| Frontend deploy | [`docs/FRONTEND_DEPLOY.md`](../FRONTEND_DEPLOY.md) | Live working-tree publish via [`scripts/deploy/deploy-live.sh`](../../scripts/deploy/deploy-live.sh); a step inside RB-1, not RB-1 |
| Deploy troubleshooting | [`deploy/TROUBLESHOOTING.md`](../../deploy/TROUBLESHOOTING.md) | 502 / stale static; host-specific |
| Security incident triage | [`docs/security/security-review-checklist.md`](../security/security-review-checklist.md) § IR | Data leak, credential compromise, malware upload |
| Detection alert triage | [`docs/security/detection-runbooks.md`](../security/detection-runbooks.md) | Per-rule security triage |
| Security runtime cycle checks | [`docs/security/operations/security-runtime-cycle-checklists.md`](../security/operations/security-runtime-cycle-checklists.md) | Staging log validation, worker audit |
| Phase 2.1 schema drop | [`docs/specs/runbooks/phase-2-1-drop-runbook.md`](../specs/runbooks/phase-2-1-drop-runbook.md) | One-off migration canary; insider context |
| Meta Lead Ads setup | [`docs/specs/integrations/meta_leads_setup.md`](../specs/integrations/meta_leads_setup.md) | Integration onboarding; contains environment-specific credentials |

Service-incident response (RB-10) is **not** covered by the security incident runbooks: those answer “data may have leaked”, not “the customer’s service is down and someone must tell them”.

---

## Rules for this folder

1. One procedure per file, `docs/runbooks/<slug>.md`, referenced from this index and from the slice that requires it.
2. Every runbook ends with an **Execution log** table: date · operator · target · build · observed result. Empty log = never executed.
3. No runbook may require knowledge that is not in the repository or in another linked runbook. If it does, it is not finished.
4. Legacy operational notes stay where they are until a slice supersedes them; this index links them rather than duplicating them.
5. Adding a required runbook to the v1 set is a change to blocker 6 scope — do it in [Operate & Launch](../specs/tasks/operate-and-launch.md), not here.

---

## History

- 2026-08-31 (later, RB-1): Deploy-from-store procedure written — [rb-1-deploy-release-build.md](rb-1-deploy-release-build.md). Status **DRAFT / NOT EXECUTED**. Does not tag and does not cut over production.
- 2026-08-31 (later, OL-2D): RB-3 still MISSING as a procedure. Predecessor is defined as a contract-satisfying deployable state; production is not one — [OL-2D](../specs/tasks/operate-launch-ol2d-predecessor.md).
- 2026-08-31: **Required set sealed by the [Launch Ownership Gate](../specs/gates/launch-ownership-gate.md) (OL-1).** Owners changed from role names to the person who holds them, because the gate requires a named holder — a release question cannot be answered by a role that has no occupant. The set itself is unchanged and still ten of ten MISSING; OL-1 was required to make the gap owned and countable, not to close it. One honest loss: RB-9's Security co-sign is now visibly the same person as its owner.
- 2026-08-28: Index introduced with the ten required v1 procedures, all MISSING, while briefing Operate & Launch as v1 blocker 6. Governance already targeted `docs/runbooks/` ([documentation-rules.md](../governance/documentation-rules.md) §2.1); this is the folder’s first file.
