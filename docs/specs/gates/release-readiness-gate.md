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
| **EC-6** | The [unowned work register](v1-unowned-work-register.md) has **no undecided D4 row** — every item is either owned by a slice or a declared residual with owner. **Met 2026-08-28** — U-6 was opened and decided the same day (fix before RC via TI-1…TI-4). Re-checked at gate opening, since a U-row may be opened at any time | [Unowned work register](v1-unowned-work-register.md) § D4 |

---

## The seven questions (normative)

Each question has one owner and one evidence artifact. “Works on my machine”, “code exists”, and “a developer can do it” are never evidence.

| # | Question | Owner | Fail if |
|---|----------|-------|---------|
| **RR1** | **Capability completeness.** Is every v1 blocker closed with a release delta that names what became true, is no blocker OPEN, and does every blocker path have a **named owning module**? | Operational lead | A blocker is closed by program outcome only; a blocker is waived without appearing in § Named residuals; a blocker path runs through a domain with no ownership card ([coverage record](module-ownership-coverage.md) MOC-1…MOC-3) |
| **RR2** | **Product acceptance.** Did a **non-developer** walk every release-blocking scenario of the [acceptance suite](../journeys/release-readiness-acceptance-suite.md) on the RC build, in one tenant, in order? | UX / product owner | Scenarios executed by the implementer, on a dev branch, across several builds, or partially |
| **RR3** | **Operability.** Can the service be deployed, rolled back, monitored, and recovered by following a written runbook — by someone who did not build it? | Engineering lead | Deploy is an undocumented manual build; no verified restore; no alerting; no on-call owner |
| **RR4** | **Tenant lifecycle.** Can an operator create a tenant, load a customer’s existing data, export all of it, and delete it — as product, not as SQL? | Operational lead | Onboarding requires developer intervention; import/export/delete exist only as scripts or not at all |
| **RR5** | **Security & compliance.** Is tenant isolation proven, are legal obligations (RODO/GDPR access, export, erasure, DPA), uploads handling, and public-surface abuse protection answered? | Security owner | Isolation asserted but untested; erasure/export unavailable; unscanned uploads accepted; fail-open protections undeclared. **Known blocker as of 2026-08-28, owned:** database-level isolation is not in force — 102 of 226 tenant-scoped tables carry no RLS policy, `FORCE ROW LEVEL SECURITY` is set nowhere, and the application role is superuser with `BYPASSRLS`, while the security canon asserts 100% coverage. Decided the same day to close it before RC — [TI-1…TI-5](../tasks/tenant-isolation-enforcement.md), was [U-6](v1-unowned-work-register.md). **Progress 2026-08-29:** the coverage guard is live with the gap frozen; all 126 policies that could raise instead of denying are rewritten; the connection is split so migrations and platform seeding run as the owner while request serving does not; and the isolation suite passes with the application connected as a non-superuser, non-owner role without `BYPASSRLS` — PostgreSQL itself refuses the other tenant's rows. Two facts this question must not lose: the previous per-request tenant binding did not survive a commit, so RLS could not have worked at all before this change; and the role is **not** switched on in any environment yet, by decision, because 102 tables still carry no policy. What remains for RR5 is TI-4: those tables, the 10 application paths that write with no tenant bound, and the decision about identity lookup once `users` carries a policy |
| **RR6** | **Quality baseline.** Which suites must be green for a release build, and is the set of tolerated known failures **enumerated, frozen, owned, and non-growing**? | Engineering lead | The blocking suite set is undefined; known failures are a moving aggregate number; a required suite is advisory. **Also fails if the number is not reproducible.** Reproducibility was obtained on 2026-08-29 — two consecutive runs of `scripts/testing/measure-known-failures.sh` gave an identical 370-id set ([measurement record](../tasks/stabilize-integration-pytest-baseline.md)) — so any figure quoted here must come from that script; a number measured on a reused database is not evidence. What remains for this question is the blocking suite set, CI reproduction, and the expiry on the tolerated set |
| **RR7** | **Support & recovery.** When the first customer breaks, is there a named path: diagnose → escalate → mitigate → roll back → communicate? | Operational lead | Incident path exists only in someone’s head; no rollback window; no customer-facing communication owner |

### Evidence bar

| Question | Acceptable evidence | Not acceptable |
|----------|---------------------|----------------|
| RR1 | Release delta lines quoted from each program close + ownership card present for every domain on a blocker path (MOC-1…MOC-3 merged) | Merged PR list; «the module obviously belongs to someone» |
| RR2 | Signed suite run: scenario ids, build id, tenant id, operator name, defect ids | Screenshots without build id; “we tested it” |
| RR3 | Runbook executed on a clean target + restore drill record (date, RPO/RTO observed) | Runbook that has never been executed |
| RR4 | One tenant created → data imported → full export produced → tenant deleted, all via product surfaces | `psql` transcript; purge script |
| RR5 | Security review checklist for the release perimeter + isolation test evidence **produced under the production-shaped database role** + a coverage guard that fails when a `tenant_id` table has no policy + named legal answer per obligation | “RLS is on” — measurement on 2026-08-28 showed that sentence to be untrue |
| RR6 | Named CI workflows with required status + frozen known-failure list with owner and expiry, **reproducible by a second person** via `scripts/testing/measure-known-failures.sh` on a fixed commit | Aggregate pass rate; a count measured on a reused database |
| RR7 | Incident runbook + rollback proven on the RC + named on-call and communication owner | Escalation implied by org chart |

---

## Outcomes

| Outcome | Meaning | Constraint |
|---------|---------|------------|
| **PASS** | All seven answered; v1 is release-ready; a paying tenant may be onboarded | No residual may touch RR1–RR5 |
| **PASS_WITH_CONSTRAINTS** | Release allowed with **named residuals**, each with owner, expiry, and customer-visible impact | Only for RR6–RR7 residuals, or an RR1–RR5 residual explicitly accepted in writing by the owner of that question |
| **STOP** | One or more questions unanswered or answered by intent | Do not onboard a paying tenant; do not announce availability |

A residual is valid only if it appears in **§ Named residuals** of the closing record with owner, expiry, and the sentence a customer would be told. Silent residuals make the outcome STOP retroactively. The candidate set of residuals is not improvised at gate time — it is the D2 section of the [unowned work register](v1-unowned-work-register.md).

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
        + Σ (remaining slice estimates on the critical path of the queue) / delivery rate
        + acceptance suite execution window
        + defect-fix window
```

Slice estimates live in the owning briefs; the roll-up lives in the [sequential queue](../tasks/sales-to-comms-sequential-queue.md) § Release horizon roll-up. This gate consumes those numbers and never overrides them.

**Current computation (from the roll-up, 2026-08-29):** 35–52 remaining slices across the Product critical path, the Launch-ops track and the gate prerequisites. Under the planning scenario (1 slice/day, chosen because the remaining work is runtime and infrastructure rather than contract slices) the RC can be tagged **2026-10-03 … 2026-10-20** and this gate would decide **2026-10-17 … 2026-11-10**. The optimistic and conservative bands, and the inputs that move them, are in the roll-up. The band has moved twice, both times because [tenant isolation](../tasks/tenant-isolation-enforcement.md) was measured more precisely: from 2026-09-27…10-11 when TI entered the prerequisites, and by one slice on 2026-08-29 when the restricted role was connected for the first time and the real cost of closing the gap became visible.

Two conditions make even that band provisional: the [unowned work register](v1-unowned-work-register.md) § D4 must be emptied before the gate may open, and the fresh-database migration failure inside [Operate & Launch](../tasks/operate-and-launch.md) OL-2 currently makes RC condition 4 unsatisfiable. A date announced without a queue roll-up behind it is not a release date.

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

- 2026-08-29: RR6 has a reproducible number — `scripts/testing/measure-known-failures.sh` produced an identical 370-id failure set on two consecutive runs, so the evidence bar now names the script and rejects figures taken from a reused database. The question still fails on the blocking suite set and CI reproduction.
- 2026-08-28: **U-6 opened and decided the same day.** The QB-1 measurement found database-level tenant isolation inert (102 of 226 tenant tables without RLS, zero `FORCE`, superuser application role with `BYPASSRLS`); the owner chose to close the gap before RC via [TI-1…TI-4](../tasks/tenant-isolation-enforcement.md) rather than amend the security canon downwards, so EC-6 is met again and RR5 has a named owner. RR5 and RR6 now carry concrete measured blockers instead of generic fail conditions, and RR6's evidence bar requires the number to be reproducible by a second person.
- 2026-08-28: RR1 extended — a blocker path running through a domain with no ownership card fails the question; MOC-1…MOC-3 delivered the three missing cards the same day. All five original D4 rows decided.
- 2026-08-29: RR5 gains real evidence — the isolation suite passes under a non-superuser, non-owner role without `BYPASSRLS`, and the unsafe policy forms are gone. The role is deliberately not switched on until TI-4 closes the 102 uncovered tables. § Derived RC date recomputed to 35–52 slices (RC 2026-10-03 … 2026-10-20 under S2).
- 2026-08-28: EC-6 added (unowned work register must have no undecided D4 row); § Derived RC date now carries the computed band from the queue roll-up instead of only a formula.
- 2026-08-28: Introduced. The Release Goal declared this control layer on 2026-08-26 without a procedure; this file supplies entry conditions, seven questions, evidence bar, RC definition, derived-date rule, and the closing template.
