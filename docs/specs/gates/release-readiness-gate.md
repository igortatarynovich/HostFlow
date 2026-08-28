# HostFlow v1 — Release Readiness Gate

**Status:** **L2 OPERATING CANON** (release close-out — the only gate that may declare HostFlow v1 release-ready)
**Date:** 2026-08-28
**Owner:** Engineering lead + Operational lead (release decision); Security owner co-signs RR5
**Trusted base:** `integration/release-product-a-b`
**Parents:** [HostFlow v1 Release Goal](hostflow-v1-release-goal.md) · [Goal Completion Gate](goal-completion-gate.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md) · [Hierarchy of Truth](../../governance/hierarchy-of-truth.md)
**Acceptance instrument:** [Release Readiness acceptance suite](../journeys/release-readiness-acceptance-suite.md)

> The [Release Goal](hostflow-v1-release-goal.md) says **what must become true**.
> This gate says **who checks that it became true, on what build, with what evidence**.
> A program PASS is never a release PASS. Queue empty is never release-ready.

---

## Why this gate exists

The Release Goal § Control layers already names a **Release Readiness Gate** and assigns it the question *“whether the product (not the last program) is done.”* Until this file existed, that layer was declared but had no procedure, no owner, and no evidence bar — so the only reachable outcome was “all named slices merged,” which the Release Goal explicitly rejects.

Two failure modes this gate must prevent:

| Failure mode | How it happens without this gate |
|--------------|----------------------------------|
| **Capability illusion** | Every v1 blocker gate PASSes on its own brief; nobody walks the finite criterion end to end on one build with one tenant |
| **Operability illusion** | The product works on a developer machine; nobody proved it can be deployed, backed up, restored, onboarded, exported, or deleted by an operator |

---

## When it is mandatory

Apply this gate before **any** of the following is claimed:

- HostFlow v1 is **release-ready** / GA
- A **first paying tenant** may be onboarded on a commercial contract
- The [Release Goal](hostflow-v1-release-goal.md) finite criterion is satisfied
- Marketing / sales may announce availability

Do **not** apply this gate to a single program close-out — that is the [Goal Completion Gate](goal-completion-gate.md). The two are orthogonal: Goal Completion asks *“did this phase remove its original problem?”*; this gate asks *“is the product operable by a paying customer?”*

---

## Entry conditions (checked before the gate opens)

The gate may not open until all of the following hold. An unmet entry condition is not a STOP — it means the gate has not started.

| # | Entry condition | Where verified |
|---|-----------------|----------------|
| **EC-1** | Every v1 blocker in [Release Goal § Confirmed v1 blockers](hostflow-v1-release-goal.md) has a **program close** with both `program outcome` and `release delta`; none remains OPEN | Release Goal § Program close |
| **EC-2** | The four checks (runtime authority · operator surface · E2E consumption · release acceptance) hold for each blocker | Release Goal § Four checks |
| **EC-3** | A **Release Candidate** exists per § Release Candidate below | This file |
| **EC-4** | The [acceptance suite](../journeys/release-readiness-acceptance-suite.md) is executable end to end on that RC by a non-developer | Suite § Execution protocol |
| **EC-5** | `make repo-health` PASS on the RC commit; trusted base fast-forward only | [Repository Operational Canon](../../governance/repository-operational-canon.md) |

---

## The seven questions (normative)

Each question has one owner and one evidence artifact. “Works on my machine”, “code exists”, and “a developer can do it” are never evidence.

| # | Question | Owner | Fail if |
|---|----------|-------|---------|
| **RR1** | **Capability completeness.** Is every v1 blocker closed with a release delta that names what became true, and is no blocker OPEN? | Operational lead | A blocker is closed by program outcome only, or a blocker is waived without appearing in § Named residuals |
| **RR2** | **Product acceptance.** Did a **non-developer** walk every release-blocking scenario of the [acceptance suite](../journeys/release-readiness-acceptance-suite.md) on the RC build, in one tenant, in order? | UX / product owner | Scenarios executed by the implementer, on a dev branch, across several builds, or partially |
| **RR3** | **Operability.** Can the service be deployed, rolled back, monitored, and recovered by following a written runbook — by someone who did not build it? | Engineering lead | Deploy is an undocumented manual build; no verified restore; no alerting; no on-call owner |
| **RR4** | **Tenant lifecycle.** Can an operator create a tenant, load a customer’s existing data, export all of it, and delete it — as product, not as SQL? | Operational lead | Onboarding requires developer intervention; import/export/delete exist only as scripts or not at all |
| **RR5** | **Security & compliance.** Is tenant isolation proven, are legal obligations (RODO/GDPR access, export, erasure, DPA), uploads handling, and public-surface abuse protection answered? | Security owner | Isolation asserted but untested; erasure/export unavailable; unscanned uploads accepted; fail-open protections undeclared |
| **RR6** | **Quality baseline.** Which suites must be green for a release build, and is the set of tolerated known failures **enumerated, frozen, owned, and non-growing**? | Engineering lead | The blocking suite set is undefined; known failures are a moving aggregate number; a required suite is advisory |
| **RR7** | **Support & recovery.** When the first customer breaks, is there a named path: diagnose → escalate → mitigate → roll back → communicate? | Operational lead | Incident path exists only in someone’s head; no rollback window; no customer-facing communication owner |

### Evidence bar

| Question | Acceptable evidence | Not acceptable |
|----------|---------------------|----------------|
| RR1 | Release delta lines quoted from each program close | Merged PR list |
| RR2 | Signed suite run: scenario ids, build id, tenant id, operator name, defect ids | Screenshots without build id; “we tested it” |
| RR3 | Runbook executed on a clean target + restore drill record (date, RPO/RTO observed) | Runbook that has never been executed |
| RR4 | One tenant created → data imported → full export produced → tenant deleted, all via product surfaces | `psql` transcript; purge script |
| RR5 | Security review checklist for the release perimeter + isolation test evidence + named legal answer per obligation | “RLS is on” |
| RR6 | Named CI workflows with required status + frozen known-failure list with owner and expiry | Aggregate pass rate |
| RR7 | Incident runbook + rollback proven on the RC + named on-call and communication owner | Escalation implied by org chart |

---

## Outcomes

| Outcome | Meaning | Constraint |
|---------|---------|------------|
| **PASS** | All seven answered; v1 is release-ready; a paying tenant may be onboarded | No residual may touch RR1–RR5 |
| **PASS_WITH_CONSTRAINTS** | Release allowed with **named residuals**, each with owner, expiry, and customer-visible impact | Only for RR6–RR7 residuals, or an RR1–RR5 residual explicitly accepted in writing by the owner of that question |
| **STOP** | One or more questions unanswered or answered by intent | Do not onboard a paying tenant; do not announce availability |

A residual is valid only if it appears in **§ Named residuals** of the closing record with owner, expiry, and the sentence a customer would be told. Silent residuals make the outcome STOP retroactively.

---

## Release Candidate (definition)

“Release Candidate” is not a mood. RC exists when:

1. A commit on the trusted base is tagged as RC and scope is frozen — only defect fixes may land afterwards.
2. That exact build is deployed to a target that is **not** a developer machine, with the same procedure production will use.
3. Frontend artifacts are built from that commit by a reproducible procedure (a manual build from untracked local output is not an RC).
4. Migrations apply to a **freshly created** database by the documented procedure, without manual repair steps.
5. A dedicated acceptance tenant is created on that build through product surfaces.

Any change to scope after RC invalidates the RC and any partially executed suite run.

---

## Release Candidate date (derived, never promised)

The RC date is **computed**, not declared:

```text
RC date = today
        + Σ (remaining slice estimates on the critical path of the queue)
        + acceptance suite execution window
        + defect-fix window
```

Slice estimates live in the owning briefs; the rolled-up horizon lives in the [sequential queue](../tasks/sales-to-comms-sequential-queue.md) execution header. This gate consumes those numbers and never overrides them. A date announced without a queue roll-up behind it is not a release date.

---

## Relationship to other gates

| Gate | Asks | Does not answer |
|------|------|-----------------|
| Named slice gates (CL*, E*, RPM*, R*) | Did this slice do what its brief said? | Whether the product is usable |
| [Goal Completion Gate](goal-completion-gate.md) | Did this phase permanently remove its original problem? | Whether the remaining phases exist |
| [Architecture Review checklist](../architecture/architecture-review-checklist.md) | Ownership / adapter / Catalog correctness | Operability |
| **This gate** | Can a paying customer be served on this build? | Which slice runs next (that is the queue) |

---

## Template (copy into the closing PR)

```text
Release Readiness Gate — HostFlow v1
RC: <tag> / <commit> / deployed at <target> on <date>
Suite run: <operator> / <tenant id> / scenarios <RS-…> / defects <ids>
RR1 Capability completeness (release deltas):
RR2 Product acceptance (suite result):
RR3 Operability (deploy + restore drill):
RR4 Tenant lifecycle (create / import / export / delete):
RR5 Security & compliance (isolation + legal + uploads + public surface):
RR6 Quality baseline (required suites + frozen known failures):
RR7 Support & recovery (incident path + rollback proof):
Named residuals: <id | owner | expiry | what the customer is told>
Outcome: PASS | PASS_WITH_CONSTRAINTS | STOP
```

---

## What this gate is not

- Not a slice, not a Product Track item, and not a program — it consumes programs
- Not a substitute for per-slice named gates or the Goal Completion Gate
- Not a licence to add v1 scope: in-scope vs later stays in the [Release Goal](hostflow-v1-release-goal.md)
- Not a schedule: slice order stays in the [sequential queue](../tasks/sales-to-comms-sequential-queue.md)
- Not a post-release quality process (steady-state operations are owned by the operational canon, not by this gate)

---

## History

- 2026-08-28: Introduced. The Release Goal declared this control layer on 2026-08-26 without a procedure; this file supplies entry conditions, seven questions, evidence bar, RC definition, derived-date rule, and the closing template.
