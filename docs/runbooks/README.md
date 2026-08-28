# Runbooks — index

**Status:** L3 IMPLEMENTATION CONTEXT (procedures) · index is **normative for the required set**
**Date:** 2026-08-28
**Owner:** Operational lead (procedure set) + Engineering lead (deploy / recovery procedures)
**Parents:** [Operate & Launch](../specs/tasks/operate-and-launch.md) (v1 blocker 6) · [Release Readiness Gate](../specs/gates/release-readiness-gate.md) RR3 / RR4 / RR7 · [Documentation rules](../governance/documentation-rules.md) §2.1 (`docs/runbooks/<slug>.md`) · [Hierarchy of Truth](../governance/hierarchy-of-truth.md)

> A runbook is a procedure a person who did not build the system can follow to a known outcome.
> This index exists so that **missing** procedures are countable instead of assumed. A row marked MISSING is a launch gap, not a TODO.
> **Executed** means a dated record exists naming operator, target, build and observed result. A runbook that has never been executed does not satisfy the [gate’s evidence bar](../specs/gates/release-readiness-gate.md) § Evidence bar.

---

## Required set for v1

| # | Runbook | Answers | Owner | Written by | Status |
|---|---------|---------|-------|------------|--------|
| **RB-1** | Deploy a release build | RR3 | Engineering lead | [OL-2](../specs/tasks/operate-and-launch.md) | **MISSING** — only [FRONTEND_DEPLOY.md](../FRONTEND_DEPLOY.md) (frontend step) and [deploy/TROUBLESHOOTING.md](../../deploy/TROUBLESHOOTING.md) exist |
| **RB-2** | Apply migrations to a fresh and to an existing database | RR3, RC condition 4 | Engineering lead | [OL-2](../specs/tasks/operate-and-launch.md) | **MISSING** — `alembic upgrade heads` currently fails on a fresh DB ([AGENTS.md](../../AGENTS.md) § Migration caveats) |
| **RB-3** | Roll back a release | RR3, RR7 | Engineering lead | [OL-2](../specs/tasks/operate-and-launch.md) | **MISSING** — no rollback procedure anywhere in the repo |
| **RB-4** | Start / verify background processing (queue worker, scheduler) | RR3 | Engineering lead | [OL-3](../specs/tasks/operate-and-launch.md) | **MISSING** — [job_queue.md](../specs/architecture/job_queue.md) describes the model, not the operation |
| **RB-5** | Monitor and respond to alerts | RR3, RR7 | Operational lead | [OL-4](../specs/tasks/operate-and-launch.md) | **MISSING** — [observability.md](../specs/platform/observability.md) §3 names alerts that nothing loads |
| **RB-6** | Back up database and document storage | RR3 | Engineering lead | [OL-5](../specs/tasks/operate-and-launch.md) | **MISSING** — no backup tooling in the repo |
| **RB-7** | Restore from backup (recovery drill) | RR3, RS-12 | Engineering lead | [OL-5](../specs/tasks/operate-and-launch.md) | **MISSING** — drill required by [RS-12](../specs/journeys/release-readiness-acceptance-suite.md) |
| **RB-8** | Onboard a tenant (create, configure, load data) | RR4, RS-10 | Operational lead | [OL-6](../specs/tasks/operate-and-launch.md) | **MISSING** — provisioning API/UI exists; procedure does not |
| **RB-9** | Export and erase a tenant’s data | RR4, RR5, RS-11 | Operational lead + Security owner | [OL-6](../specs/tasks/operate-and-launch.md) | **MISSING** — capability itself absent; contract in [ADR-039](../specs/architecture/ADR-039-tenant-data-lifecycle.md) |
| **RB-10** | Incident response: diagnose → escalate → mitigate → roll back → communicate | RR7 | Operational lead | [OL-7](../specs/tasks/operate-and-launch.md) | **MISSING** for service incidents — security incidents are covered (see below) |

Ten required procedures, ten missing. That count is the honest measure of operational readiness today.

---

## Existing procedures (not part of the required v1 set, kept as-is)

| Procedure | Path | Scope |
|-----------|------|-------|
| Frontend deploy | [`docs/FRONTEND_DEPLOY.md`](../FRONTEND_DEPLOY.md) | Build + Caddy restart; a step inside RB-1, not RB-1 |
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

- 2026-08-28: Index introduced with the ten required v1 procedures, all MISSING, while briefing Operate & Launch as v1 blocker 6. Governance already targeted `docs/runbooks/` ([documentation-rules.md](../governance/documentation-rules.md) §2.1); this is the folder’s first file.
