# HostFlow v1 — Release Goal

**Status:** **L2 OPERATING CANON** (v1 in-scope vs later; Release DAG ≠ slice schedule)  
**Phase class:** platform  
**Date:** 2026-08-26  
**Trusted base:** `integration/release-product-a-b`  
**Parents:** [Sequential queue](../tasks/sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Goal Completion Gate](goal-completion-gate.md) · [Hierarchy of Truth](../../governance/hierarchy-of-truth.md) · [Documents Platform E8-eval](../tasks/documents-platform-e8-eval.md)  
**Close-out instruments:** [Release Readiness Gate](release-readiness-gate.md) (who declares v1 ready) · [Release Readiness acceptance suite](../journeys/release-readiness-acceptance-suite.md) (how it is proven)  
**Product Track:** **[RPM-1](../tasks/requirement-policy-management.md)** (brief; feat locked) — scheduled in the [sequential queue](../tasks/sales-to-comms-sequential-queue.md) after [#328](https://github.com/igortatarynovich/HostFlow/pull/328). This file does not invent slice order.

> This document is the **v1 in-scope vs later** SoT.  
> The [sequential queue](../tasks/sales-to-comms-sequential-queue.md) remains the **slice schedule** SoT (one Active Product).  
> Horizon letters in the [roadmap](../architecture/platform-completion-roadmap.md) (OCR, packages, Billing, AI) are **not** v1.  
> First Product from § Release DAG is **Requirement Policy Management**, scheduled as [RPM-1](../tasks/requirement-policy-management.md) (brief; feat locked). This file does **not** lock a linear program order of the five blockers. Mapping remains startable after RPM program close — not auto-scheduled here.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
A locked sequential queue can reach a program horizon (E8-eval) while the product is not releasable, because slice gates never asked whether the **Release Goal** became true. Roadmap leftovers must not silently become the next Product.

**Completion proof (named consumer):**  
A first paying tenant operated by a non-developer: configure without code → external candidate in → mapped canonical entities → recruitment with operator-managed requirements and documents → communication → hire → minimum Employee, proven by the [Release Readiness acceptance suite](../journeys/release-readiness-acceptance-suite.md) (§ Finite criterion).

---

## Finite criterion

HostFlow v1 is **release-ready** when a tenant can be configured without code, acquire an external candidate, map source data into canonical entities, operate the candidate through recruitment using operator-managed requirements and documents, communicate with the candidate, complete hiring, transfer the person into the minimum employee state — **and** when that tenant can be deployed onto, recovered, exported and offboarded by an operator who did not build the system ([blocker 6](../tasks/operate-and-launch.md)) — proven by the [Release Readiness acceptance suite](../journeys/release-readiness-acceptance-suite.md).

Close-out of v1 is this criterion **plus** the [Goal Completion Gate](goal-completion-gate.md) against this section — not “all named slices in an amendment merged.”

The criterion is **declared true only by** the [Release Readiness Gate](release-readiness-gate.md). No program close, queue horizon, or blocker gate may declare it.

---

## Four checks (mandatory on every v1 blocker)

A Settings page that edits non-authority JSON is **not** ready. All four must hold, or the capability is **OPEN**.

| Check | Meaning |
|-------|---------|
| **Runtime authority** | One answerer, or an explicit contract between answerers |
| **Operator surface** | A person manages **that** authority |
| **E2E consumption** | The setting changes the working flow |
| **Release acceptance** | A named scenario in the [acceptance suite](../journeys/release-readiness-acceptance-suite.md) proves the operator job |

---

## Confirmed v1 blockers

| # | Capability | v1 boundary (acceptance) |
|---|------------|--------------------------|
| **1** | **Requirement Policy Management** — [brief](../tasks/requirement-policy-management.md) (Active: RPM-1) | For this tenant / client / vacancy / profile / country: these requirements apply; base rule; override; reason; result. Documents is the **first domain** of this capability — not a second Documents Admin vs Rules Admin product. |
| **2** | **Mapping Authority** — [brief](../tasks/mapping-authority.md) (queued) | One operator-visible model from source answers to **canonical entity fields**. Not “build another mapping editor.” |
| **3** | **External Intake / Forms Publish** — [brief](../tasks/external-intake-forms-publish.md) (queued) | `publish → public form → submit → mapping → canonical entity → visible in workspace`. Forms P4 / P5 stay later. |
| **4** | **Hiring workflow E2E** — [brief](../tasks/hiring-workflow-e2e.md) (queued) | One candidate: `stage → requirements/docs → eligibility → transfer`. Acceptance over existing funnels, gates, policy authority, and transfer — **not** a new Hiring Product. |
| **5** | **Minimal Recruitment → HR handoff** — [brief](../tasks/recruitment-hr-minimal-handoff.md) (queued) | Hire / transfer creates or links Employee; identity / profile kept; documents reused via Document Link; handoff status visible; no manual copy. Full HR operations (Kadry, payroll, extended lifecycle) are later. |
| **6** | **Operate & Launch** — [brief](../tasks/operate-and-launch.md) (**active**; **Launch-ops track** opened 2026-08-31, [OL-1](launch-ownership-gate.md) done, OL-2 next) | Deployed, rolled back, monitored, backed up and restored from written procedures; tenant created, loaded, exported and erased as product; support and incident path named. Not an SRE programme, not IaC, not steady-state operations. |

Blockers 1–5 are **capability** blockers: they make the product complete. Blocker 6 is an **operability** blocker: it makes the product sellable. Blocker 6 is not a capability node in the DAG and does not consume a Product slot — it runs as the parallel **Launch-ops** track, because a paying tenant cannot be served by features alone.

Every blocker now has a brief with `Original Goal → Completion Proof`, an internal slice ladder with named gates, and an estimate. A brief is **not** a schedule: only the [sequential queue](../tasks/sales-to-comms-sequential-queue.md) activates a slice, and the Active Product remains RPM-1.

### Supporting (must work for the five; not separate programs)

Company setup · Acquisition path into intake · Candidate workspace · Communications (Epic C constraints; C2.4 frozen) · Permissions sufficient to operate.

These are **acceptance dependencies**, not automatic extra programs. A new Product exists only if a **release-blocking gap** is found in one of them. Communications, for example, is proven via the existing path with named constraints — it is not rebuilt as a v1 program.

---

## Control layers (do not collapse)

| Layer | Answers | Must not |
|-------|---------|----------|
| **Release Goal** (this file, finite criterion) | What must become **true** for v1 | Invent the next slice |
| **Release DAG** (§ below) | Which **capabilities** provide that, and which **acceptance** edges exist | Lock execution order |
| **Program** | One capability, or a named part of one | Close the product by closing itself |
| **Sequential queue** | Actual **slice** order, one Active Product | Invent v1 scope |
| **[Release Readiness Gate](release-readiness-gate.md)** | Whether the product (not the last program) is done | Treat program PASS as v1 PASS |

A finished program writes **program outcome** + **release delta**. Queue complete without an explicit release delta does **not** mean HostFlow v1 is ready.

---

## Explicit later (conscious scope cut)

These are **out of v1**. “Later” means deferred on purpose, not unfinished.

| Theme | v1 statement |
|-------|----------------|
| OCR | Out of v1 |
| Document packages | Out of v1 |
| AI | Out of v1 |
| General automation control plane | v1 **does not** promise a general-purpose automation control plane. Existing reminders and communication Intent rules stay **feature-specific**. [ADR-019](../architecture/ADR-019-automation-capability-entitlement-control-plane.md) Reaction Orchestrator remains target architecture; it does **not** block release. |
| Tenant extension / widget system | HostFlow **owns and ships** all v1 workspace blocks first-party. Marketplace, install/uninstall, extension manifests, third-party widget lifecycle — later. |
| Self-service Billing | v1 supports **operator-assisted** commercial onboarding (contract → invoice → manual tenant/plan). Self-service plans, subscriptions, limits, invoices UI = Phase F. Stripe skeleton may remain infrastructure. |
| Full HR operations | Beyond the minimum handoff in blocker 5 |
| Forms P4 / P5 | Themes / analytics after publish path works |

Do **not** treat a later theme as the next Product because it appears in the roadmap.

---

## Release DAG (capabilities + acceptance edges — not a queue)

Grain: **capabilities**, not slices. This is **not** a sequential Product ladder. Linear slice order appears only in a later **docs-only queue amendment** after dependency analysis. Unlock ≠ schedule. The first such amendment after [#328](https://github.com/igortatarynovich/HostFlow/pull/328) scheduled [RPM-1](../tasks/requirement-policy-management.md); it did **not** lock a total order of the five blockers.

```text
Release Goal (finite criterion)
        │
        │     five blocker capabilities (a set, not a ladder)      Launch-ops track (parallel)
        ├─ Requirement Policy Management                           ┌─ Operate & Launch (blocker 6)
        ├─ Mapping Authority                                       │    deploy · rollback · signal
        ├─ External Intake / Forms Publish                         │    backup · restore
        ├─ Hiring workflow E2E                                     │    tenant lifecycle · support
        └─ Minimal Recruitment → HR handoff                        └────────────┐
        │                                                                       │
        ▼                                                                       │
dependency / integration gates (acceptance edges below)                         │
        │                                                                       │
        ▼                                                                       │
Release Candidate  ◄──── requires a deploy procedure + clean migrations ────────┘
        │
        ▼
Release Readiness Gate
```

Blocker 6 is drawn beside the capability set, not inside it: it is a precondition of the **Release Candidate** node (a tagged build deployed to a non-developer target with migrations applied to a fresh database) and of readiness questions RR3 / RR4 / RR7. It has no acceptance edge to or from any capability.

The last two nodes are defined in one place: **Release Candidate** (what build acceptance runs on), the seven readiness questions, and the outcome vocabulary all live in the [Release Readiness Gate](release-readiness-gate.md). This file does not restate them.

Supporting capabilities (Company setup, Acquisition, Candidate workspace, Communications, Permissions) attach as **acceptance dependencies** of the five, not as extra DAG nodes and not as extra programs.

**Known acceptance edges** (what a capability’s release acceptance consumes — **not** proven execution order):

| Edge | Why |
|------|-----|
| Mapping Authority → External Intake | Intake acceptance is `publish → … → mapping → canonical entity` |
| Requirement Policy Management → Hiring E2E | Hiring acceptance walks `stage → requirements/docs → eligibility → transfer` against policy authority |
| Hiring E2E → Min HR handoff | Handoff acceptance needs a completed hire/transfer of one person |

**Not proven as execution predecessors** (do **not** treat as queue order):

- Requirement Policy Management before Mapping Authority  
- Requirement Policy Management before External Intake  
- Min HR handoff blocked on Forms / External Intake  
- Any total order of the five blockers  

Programs may run with limited parallelism where write sets do not overlap. They do **not** mint a third track. After a program horizon the next **Product** is chosen from this DAG by a queue amendment — not invented from the roadmap.

---

## Program close = two results

A program may not close with only “horizon reached.” Both lines are mandatory:

| Field | Meaning |
|-------|---------|
| **Program outcome** | What the program finished technically |
| **Release delta** | Which Release Goal condition became true; which v1 blockers remain OPEN |

### E8-eval (already shipped)

| Field | Value |
|-------|--------|
| **Program outcome** | D4 evaluates document requirements through canonical R5 `merge(pack, tenant_delta)` |
| **Release delta** | Requirement **evaluation** is partially satisfied. Requirement Policy Management remains **OPEN**. Mapping Authority, External Intake, Hiring E2E, and min HR handoff remain **OPEN**. HostFlow v1 is **not** release-ready. Documents Foundation stays 🔄. |

---

## Current four-check snapshot (not acceptance)

Recorded at Goal seal. Not a PASS.

| Capability | Authority | Operator surface | E2E consumption | Acceptance |
|------------|-----------|------------------|-----------------|------------|
| Requirement Policy Management | partial (R5 on E8-eval) | no | no | OPEN |
| Mapping Authority | no (three contracts) | partial (C-5 / intake editors) | partial | OPEN |
| External Intake / Forms Publish | partial (Foundation serve→execute) | no (P3 locked) | partial | OPEN |
| Hiring workflow E2E | partial (funnels / gates / transfer) | partial | not proven vs policy authority | OPEN |
| Minimal HR handoff | partial (E3/E4 Document Link) | partial | partial | OPEN |
| Operate & Launch (blocker 6, added 2026-08-28) | no (no deploy / rollback / backup procedure — RB-1…RB-10 all MISSING, now owned and countable via [OL-1](launch-ownership-gate.md)) | partial (tenant create only; no delete, no export, no bulk import; contract accepted in [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md), capability absent) | no (in-process queue + local disk are the defaults) | OPEN |

---

## What this document does not do

- Does not schedule Mapping, External Intake, Hiring E2E, min HR, or Operate & Launch (RPM is scheduled in the sequential queue, not by this file; the Launch-ops track is opened by a queue amendment)  
- Does not lock a linear program / slice order (that is the sequential queue)  
- Does not reopen E8-eval, Overlay, CL7, DR1-runtime, or E8-bind  
- Does not mark Documents Foundation ✅  
- Does not mint Catalog events, Hub request/reminder/packages tables, or CL8  
- Does not unfreeze C2.4  

---

## Refs

- [Sequential queue](../tasks/sales-to-comms-sequential-queue.md) — slice schedule; Active Product = [RPM-1](../tasks/requirement-policy-management.md)  
- [Dependency-position review](v1-release-dag-dependency-position.md) — why RPM is first  
- [Release Readiness Gate](release-readiness-gate.md) — entry conditions, seven questions, Release Candidate, derived RC date  
- [Release Readiness acceptance suite](../journeys/release-readiness-acceptance-suite.md) — RS-1…RS-12 and the coverage matrix  
- [Goal Completion Gate](goal-completion-gate.md) — original goal vs substituted brief  
- [Platform capability maturity](../architecture/platform-capability-maturity.md) — platform maturity ≠ v1 Release Goal  
- [Operate & Launch](../tasks/operate-and-launch.md) — blocker 6 (Launch-ops track) · [Runbook index](../../runbooks/README.md) — required procedures with owner and status
- [Unowned work register](v1-unowned-work-register.md) — what v1 deliberately does not own; § D4 must be empty for the gate to open
- [Tenant isolation enforcement](../tasks/tenant-isolation-enforcement.md) — gate prerequisite for RR5, not a capability blocker: the database-level isolation the security canon claims is not yet in force
- [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) · [ADR-019](../architecture/ADR-019-automation-capability-entitlement-control-plane.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md) (tenant data lifecycle)
