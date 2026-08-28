# Release Readiness acceptance suite (v1)

**Status:** **L2 OPERATING CANON** (acceptance instrument of the [Release Readiness Gate](../gates/release-readiness-gate.md))
**Date:** 2026-08-28
**Owner:** UX / product owner (suite content) + Operational lead (execution and evidence)
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) · [Release Readiness Gate](../gates/release-readiness-gate.md) · [Journey checklists](README.md) · [personas](../personas.md) · [ADR-036 four trust roles](../architecture/ADR-036-four-trust-roles-rbac.md)

> The [Release Goal](../gates/hostflow-v1-release-goal.md) finite criterion is one long sentence.
> This file is that sentence cut into scenarios that a **non-developer** can execute in order, on one build, in one tenant.
> A scenario proves an **operator job**, never a feature’s existence.

---

## What makes a scenario release-blocking

A scenario belongs in this suite only if all four hold:

1. It maps to a clause of the finite criterion or to a question of the [Release Readiness Gate](../gates/release-readiness-gate.md).
2. It is executable by a person who cannot read code and cannot open a terminal.
3. Its pass criterion is a single observable sentence, not a checklist of clicks.
4. Failing it would mean a paying customer cannot be served.

Anything else is a QA nicety and stays in the [persona journeys](README.md).

---

## Relationship to the existing UAT material (no third protocol)

| Instrument | Role after this file | Release-blocking |
|------------|----------------------|------------------|
| **This suite** | The v1 release acceptance set; consumed by the Release Readiness Gate RR2 | **Yes** |
| [Persona journeys 2.2](README.md) (`administrator`, `recruiter`, `supervisor`, portals, …) | Per-persona QA session checklists; broader than release scope; defects still logged | No |
| [`UAT_DEFECT_LOG.md`](UAT_DEFECT_LOG.md) | Single defect register for both instruments; suite runs record defect ids here | n/a |

The suite does **not** replace persona journeys and does **not** create a second defect register. If a persona journey contradicts this suite about release scope, this suite wins; if it contradicts it about persona behaviour, the journey wins.

---

## Scenario catalog

Order is normative: scenarios build on each other’s state inside one tenant.

| id | Scenario | Proves (Release Goal) | Pass criterion (one sentence) |
|----|----------|----------------------|-------------------------------|
| **RS-1** | Tenant configured without code | “configured without code” + Company setup | An administrator brought the tenant from empty to operable — company, users with trust roles, vacancy, funnel stages, and requirement expectations — without a developer and without editing JSON by hand |
| **RS-2** | External candidate arrives through a published form | Blocker 3 — External Intake / Forms Publish | A form published from the product is reachable at a public URL, a stranger submits it, and the submission appears in the workspace as a canonical entity |
| **RS-3** | Source answers become canonical fields | Blocker 2 — Mapping Authority | An operator can see and change, in **one** place, how incoming answers land on canonical entity fields, and the next submission follows the change |
| **RS-4** | Operator changes a requirement policy | Blocker 1 — Requirement Policy Management | An operator sets what is required for a tenant / client / vacancy / profile / country, with base rule, override, and reason, and the candidate’s working flow immediately reflects it |
| **RS-5** | Document requirement lifecycle | Blocker 1 (Documents domain) | A required document is requested, provided, accepted, and later expires — and readiness recomputes each time without anyone editing a status by hand |
| **RS-6** | Communication with the candidate | Supporting — Communications | A recruiter writes to the candidate from the candidate’s own screen, and the candidate’s reply lands on the same thread bound to the same entity |
| **RS-7** | Hiring end to end | Blocker 4 — Hiring workflow E2E | One candidate moves stage → requirements/documents → eligibility → transfer, and eligibility is refused when policy says it must be |
| **RS-8** | Handoff into HR | Blocker 5 — Minimal Recruitment → HR handoff | The hired person exists as an employee with identity and profile preserved and documents reused by link, with handoff status visible and no manual re-entry |
| **RS-9** | Permission boundaries | Supporting — Permissions | A viewer and a portal guest each see exactly their permitted surface, and neither can reach tenant data outside it |
| **RS-10** | Operator onboards a new tenant with existing data | Gate RR3 / RR4 | An operator creates a fresh tenant on the release build following the runbook and loads a customer’s existing candidate base through a product surface |
| **RS-11** | Tenant data export and erasure | Gate RR4 / RR5 | An operator produces a complete export of one tenant’s data and then erases that tenant, with both results verifiable |
| **RS-12** | Recovery drill | Gate RR3 | The service is restored from backup to a known point on the release build, and a previously passed scenario still passes afterwards |

---

## Scenario definitions

Each scenario lists **preconditions**, the **operator job** (not the click path), and **evidence**. Steps deliberately avoid naming buttons: a suite that encodes today’s UI cannot survive one refactor.

### RS-1 Tenant configured without code

- **Preconditions:** empty tenant on the RC build; administrator credentials only.
- **Operator job:** create the company context, invite/assign users to trust roles, create one vacancy, define the stages the candidate will pass, and declare what will be expected from candidates.
- **Must not require:** SQL, seed scripts, environment variables, feature-flag edits, or a developer answering “where do I click”.
- **Evidence:** tenant id, administrator account, list of objects created, and the sentence “no developer participated”.

### RS-2 External candidate arrives through a published form

- **Preconditions:** RS-1 done.
- **Operator job:** build an intake form for that vacancy, publish it, obtain the public URL, and have an outsider (private browser, no account) submit it.
- **Pass detail:** the submission is visible in the workspace as a canonical entity — not only as a raw payload in an inbox.
- **Evidence:** public URL, submission timestamp, resulting entity id.

### RS-3 Source answers become canonical fields

- **Preconditions:** RS-2 produced at least one submission.
- **Operator job:** inspect how one answer reached (or failed to reach) a canonical field, change that decision in the single operator-visible model, submit again, and observe the new placement.
- **Pass detail:** exactly one place had to be changed; the operator did not have to ask which of several editors is authoritative.
- **Evidence:** before/after field placement for one named answer.

### RS-4 Operator changes a requirement policy

- **Preconditions:** RS-2 produced a candidate on a vacancy.
- **Operator job:** state a base requirement, override it for this vacancy or country with a reason, and observe the candidate’s requirement set and readiness change.
- **Pass detail:** the result is explainable on screen — which rule applied, which override won, and why.
- **Evidence:** rule, override, reason, and the candidate readiness before/after.

### RS-5 Document requirement lifecycle

- **Preconditions:** RS-4 established a required document.
- **Operator job:** request the document, receive it, accept it, then move validity past expiry and observe readiness recompute.
- **Pass detail:** no status was edited manually to make readiness change.
- **Evidence:** request id, document id, readiness states across the four transitions.

### RS-6 Communication with the candidate

- **Preconditions:** candidate from RS-2 with a reachable address.
- **Operator job:** send a message from the candidate’s screen and reply from the candidate side.
- **Pass detail:** both messages sit on one thread bound to that candidate; a delivery failure, if any, is explainable without server logs.
- **Constraint:** C2.4 Scheduling is frozen — scheduled/queued sending is out of scope for this scenario.
- **Evidence:** thread id, entity id, delivery diagnostics record.

### RS-7 Hiring end to end

- **Preconditions:** RS-4 and RS-5 done for one candidate.
- **Operator job:** progress the candidate through the defined stages, attempt transfer while a requirement is unmet (must be refused with a readable reason), satisfy it, then complete the hire.
- **Pass detail:** the refusal came from the same policy authority the operator manages in RS-4, not from a separate hard-coded rule.
- **Evidence:** stage history, refusal reason text, completion record.

### RS-8 Handoff into HR

- **Preconditions:** RS-7 completed a hire.
- **Operator job:** confirm the person exists as an employee, check that identity/profile carried over, open a document provided in RS-5 from the employee context, and read the handoff status.
- **Pass detail:** nothing was re-typed and no document was re-uploaded.
- **Evidence:** employee id, link between employee and prior candidate, document link record, handoff status.

### RS-9 Permission boundaries

- **Preconditions:** RS-1 created a viewer; a portal guest context exists.
- **Operator job:** with each restricted role, attempt to reach the tenant surfaces they must not see, including direct URL entry.
- **Pass detail:** refusals are enforced server-side, not merely hidden in navigation.
- **Evidence:** role, attempted paths, observed result per path.

### RS-10 Operator onboards a new tenant with existing data

- **Preconditions:** RC build deployed to a non-developer target; onboarding runbook available.
- **Operator job:** create a second tenant from zero following the runbook, then load a customer’s existing candidate base (a realistic file, not three rows) through a product surface.
- **Pass detail:** the operator never left the product except for steps the runbook itself prescribes.
- **Evidence:** runbook revision followed, tenant id, record counts in vs. records visible, rejected-row report.

### RS-11 Tenant data export and erasure

- **Preconditions:** RS-10 tenant populated.
- **Operator job:** produce a complete export of that tenant’s data, verify a sample against the UI, then erase the tenant and verify its data is gone from product surfaces.
- **Pass detail:** both actions were available as product operations with an audit trail.
- **Evidence:** export artifact inventory, sample verification, erasure confirmation, audit records.

### RS-12 Recovery drill

- **Preconditions:** backups configured per runbook; a scenario already passed (RS-7 recommended).
- **Operator job:** restore to a chosen point on the release build and re-verify the earlier scenario’s result.
- **Pass detail:** observed recovery point and recovery time were recorded and compared to the declared targets.
- **Evidence:** restore record, observed RPO/RTO, re-verification result.

---

## Coverage matrix (must be total)

Every v1 blocker and every gate question that this suite is responsible for must appear at least once. A blocker with no scenario cannot pass RR2.

| Release Goal item | Scenarios |
|-------------------|-----------|
| Blocker 1 — Requirement Policy Management | RS-4, RS-5, RS-7 |
| Blocker 2 — Mapping Authority | RS-3 |
| Blocker 3 — External Intake / Forms Publish | RS-2 |
| Blocker 4 — Hiring workflow E2E | RS-7 |
| Blocker 5 — Minimal Recruitment → HR handoff | RS-8 |
| Blocker 6 — [Operate & Launch](../tasks/operate-and-launch.md) (Launch-ops) | RS-10, RS-11, RS-12 |
| Supporting — Company setup / configure without code | RS-1 |
| Supporting — Acquisition path into intake | RS-2 |
| Supporting — Candidate workspace | RS-4, RS-5, RS-6 |
| Supporting — Communications | RS-6 |
| Supporting — Permissions | RS-9 |
| Gate RR3 — Operability | RS-10, RS-12 |
| Gate RR4 — Tenant lifecycle | RS-10, RS-11 |
| Gate RR5 — Security & compliance | RS-9, RS-11 |

Gate questions RR1, RR6, and RR7 are **not** proven by this suite — they are documentary/CI/process evidence collected directly by the [gate](../gates/release-readiness-gate.md). RS-10…RS-12 depend on runbooks that do not exist yet: every required procedure is listed as MISSING in the [runbook index](../../runbooks/README.md), and writing them is [Operate & Launch](../tasks/operate-and-launch.md). Until then these three scenarios are **NOT RUN — blocked**, not failing.

---

## Execution protocol

| Rule | Requirement |
|------|-------------|
| **Build** | One Release Candidate, unchanged for the whole run (see gate § Release Candidate) |
| **Operator** | A person who did not implement the scenarios; RS-1…RS-9 by a product/ops person, RS-10…RS-12 by an operator following runbooks |
| **Tenant** | RS-1…RS-9 in one acceptance tenant, in order; RS-10…RS-12 in a second tenant created during the run |
| **Order** | Normative — a later scenario may consume earlier state |
| **Defects** | Logged in [`UAT_DEFECT_LOG.md`](UAT_DEFECT_LOG.md) with scenario id; blocking defects stop the run |
| **Evidence** | Per scenario: build id, tenant id, operator, timestamp, the artifacts named in its definition |
| **Re-runs** | A scope change after RC invalidates the run; a defect fix re-runs the affected scenario and every later scenario that consumed its state |

### Result record (copy into the gate closing PR)

```text
Suite run — HostFlow v1
Build: <RC tag / commit>   Target: <where deployed>
Operators: <name (RS-1..RS-9)> / <name (RS-10..RS-12)>
Tenants: <acceptance tenant id> / <onboarding tenant id>
RS-1 … RS-12: PASS | FAIL (<defect id>) | NOT RUN (<reason>)
Blocking defects: <ids>
Coverage: every Release Goal blocker has at least one PASS scenario (yes/no)
```

---

## Waivers

A scenario may be marked NOT RUN only if the [gate](../gates/release-readiness-gate.md) records it as a **named residual** with owner, expiry, and the sentence the customer would be told. “Not run because not implemented” is a FAIL, not a waiver.

---

## What this suite is not

- Not a test plan for engineers, and not a substitute for CI (see gate RR6)
- Not the persona journey set (RS scenarios are the release-blocking subset)
- Not a scope document: adding a scenario does not add v1 scope, and v1 scope lives in the [Release Goal](../gates/hostflow-v1-release-goal.md)
- Not a schedule: execution windows feed the derived RC date in the gate

---

## History

- 2026-08-28: Introduced. The Release Goal referenced a “Release Readiness acceptance suite” from 2026-08-26 without defining it; this file supplies twelve scenarios, the coverage matrix, and the execution protocol, and subordinates persona journeys to it for release scope only.
