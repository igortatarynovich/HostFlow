# Minimal Recruitment → HR handoff

**Status:** **QUEUED** (brief only; feat locked; **not scheduled**) — Active Product is [MA-2](mapping-authority.md)
**Phase class:** platform
**Branch (docs):** `docs/v1-blocker-briefs`
**Branch (code):** none — later slices `feat/min-hr-handoff-hhN-…`
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) (blocker 5) · [Release Readiness Gate](../gates/release-readiness-gate.md) · [Acceptance suite RS-8](../journeys/release-readiness-acceptance-suite.md) · [Hiring workflow E2E](hiring-workflow-e2e.md) · [Documents E3 First Consumer Bind](documents-platform-e3-first-consumer-bind.md) ✅ · [Documents E4 Candidate Document Link](documents-platform-e4-candidate-document-link.md) ✅ · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [Sequential queue](sales-to-comms-sequential-queue.md)
**Estimate:** 4–6 slices (1 slice = one docs PR + one feat PR)

> v1 blocker 5: **hire / transfer creates or links Employee; identity / profile kept; documents reused via Document Link; handoff status visible; no manual copy.**
> Full HR operations (Kadry, payroll, extended lifecycle) stay **later**.
> **Not** Hiring E2E (that is [the predecessor](hiring-workflow-e2e.md)). **Not** a Documents phase. **Not** an HR product build-out. **Not** D10.
> Opening this brief does **not** schedule it. Hiring remains queued after RPM close. The queue’s Active Product is [MA-2](mapping-authority.md).

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
A hired person can end up existing twice — once as a candidate, once as an employee — with data re-typed by a human. Most of the machinery against that already exists (idempotent employee creation from a candidate, a candidate snapshot, `reused_for_hr` document links, HR case, status surfaces), but three things make the promise unprovable: a tenant flag (`delayed_hr_workforce_creation_enabled`) under which accepting a handoff creates **no** employee until a later approval, document reuse that silently narrows to approved requirement fulfillments (or widens to *all* candidate documents in the legacy fallback), and a handoff status split across candidate stage, handoff record, employee status and HR review with no single readable contract. Nothing forbids manual re-entry for fields outside the snapshot.

**Completion proof (named consumer):**
**RS-8 in the [acceptance suite](../journeys/release-readiness-acceptance-suite.md)**: after the hire completed in RS-7, the person exists as an employee with identity and profile preserved; a document provided during recruitment (RS-5) opens from the employee context; and one handoff status is readable — with nothing re-typed and no document re-uploaded. What this consumer must **not** fork: an HR-local copy of candidate identity or a second document attachment path for the same file.

**False close (reject):** proving it with the delayed-workforce flag disabled while production tenants would run with it enabled (or vice versa) without declaring which is the release posture; counting a `candidate_snapshot` JSON blob as “identity kept” when the employee screen still asks the operator to retype; linking all candidate documents indiscriminately and calling it reuse; treating the PE HR inbound placeholder as wired.

---

## Starting point (measured, not assumed)

Evidence collected 2026-08-28.

### Already provable today

| Capability | Where |
|------------|-------|
| Handoff create → accept → employee | `services/handoff.py` (`create_handoff`, `accept_handoff`), `services/hr_acceptance_orchestrator.py` |
| Idempotent employee link by candidate | `POST /workforce/employees/from-candidate/{candidate_id}` — “Idempotent: returns existing row if already linked”; `services/workforce_employees.py::handoff_from_candidate` |
| Identity / profile carry-over | `candidate_snapshot` + meta on the employee row; work-eligibility seeding from candidate |
| Document reuse by link | `services/workforce_hr_operational_context.py::ensure_hr_document_links` → `document_entity_links` with `relation_type="reused_for_hr"` |
| Gate before handoff | package readiness + stage requirement (`ready_for_handoff` / `ready_for_hr`) |
| Status surfaces | candidate card handoff status · `/app/hr/inbox` · `/app/hr/handoffs/:id` · `/app/hr/employees/:employeeId` (auto-redirect when the employee exists) |

### Structural problems this program must close

| # | Problem | Evidence |
|---|---------|----------|
| **1** | **Delayed workforce mode** — with `delayed_hr_workforce_creation_enabled`, accept performs HR review + document links but creates **no** employee until approval, so “transfer creates or links Employee” depends on a tenant flag | `services/hr_acceptance_orchestrator.py` (legacy path vs delayed path) |
| **2** | **Document reuse scope is conditional** — only approved fulfillment document ids are linked when available; otherwise *all* active candidate documents (legacy fallback) | `workforce_hr_operational_context.py` — “Otherwise falls back to all active candidate documents (legacy)” |
| **3** | **Identity is a snapshot copy**, not a contracted identity continuity | `candidate_snapshot` / `_handoff_meta_from_snapshot` |
| **4** | **Status has four homes** — candidate stage, handoff record, employee status, HR review — with no single contract | handoff + workforce + HR review models |
| **5** | **PE HR inbound is a declared placeholder** — the recruitment manifest targets `hr.received_from_recruitment` / `hr_case`, but the HR manifest ships `HR_INBOUND_HANDOFF_PLACEHOLDER_MODE = "inbound_contract_placeholder"` with empty pipeline templates, process profiles and transition rules; no runtime router reads it | `process_engine/manifests/hr.py`, `process_engine/manifests/recruitment.py` |
| **6** | **Manual copy is not forbidden** — fields outside the snapshot seed paths can still be retyped in the HR workspace | HR review surfaces |

Problem 5 is the one that must not be resolved by silence: either the inbound contract is wired, or it is recorded as a named residual with owner and expiry under the [Release Readiness Gate](../gates/release-readiness-gate.md) residual rule.

---

## Internal ladder (this program only)

```text
HH-1 Handoff contract seal (minimum employee, identity, reuse, one status)
  → HH-2 Status contract runtime
  → HH-3 Identity + document reuse cutover
  → HH-4 Acceptance proof + inbound-placeholder decision
  → Min HR handoff program close (outcome + release delta)
```

| # | Slice | Machine id | Named gate (PASS =) | Depends on | Estimate |
|---|-------|------------|---------------------|------------|----------|
| **HH-1** | Handoff contract seal | `hh-contract` | **HR Handoff Contract Gate** — “minimum Employee” defined field by field; identity-continuity rule stated; document-reuse scope stated (no conditional fallback); one status contract named; release posture of the delayed-workforce flag decided | Hiring E2E program close (queue amendment) | 1 slice (docs) |
| **HH-2** | Status contract runtime | `hh-status` | **Handoff Status Gate** — one readable status derived from the four stores; recruitment, HR inbox and employee surfaces show the same answer | HH-1 Gate | 1 slice |
| **HH-3** | Identity + reuse cutover | `hh-reuse` | **Handoff Reuse Gate** — required documents (per the RPM authority) are reachable from the employee context by link, never by re-upload; identity fields are carried by contract, not by snapshot luck | HH-2 Gate | 1–2 slices |
| **HH-4** | Acceptance proof | `hh-accept` | **Min HR Handoff Acceptance Gate** — RS-8 passes on the RS-7 hire with the declared release posture of the delayed flag; PE HR inbound placeholder either wired or recorded as a named residual with owner + expiry | HH-3 Gate | 1 slice |

---

## HH-1 — Handoff contract seal (queued, docs only)

Answers four questions the current implementation leaves to configuration: what the **minimum employee** must contain for v1; which identity fields must survive the transfer and how (contract, not snapshot); exactly which documents are reused and by which relation; and what a single handoff status means across recruitment and HR.

Out: Kadry, payroll, contracts lifecycle, HR product surfaces beyond status + document reuse.

## HH-2 — Status contract runtime (queued)

One status, four stores. Out: rebuilding the HR inbox; new HR screens.

## HH-3 — Identity + document reuse cutover (queued)

Removes the conditional reuse fallback and the retype paths for contracted identity fields. Out: dossier redesign, OCR, e-sign, packages.

## HH-4 — Acceptance proof + placeholder decision (queued)

RS-8 on the real hire. The PE HR inbound placeholder gets an explicit disposition here — wired, or a residual with an owner and an expiry date. It may not stay undeclared.

---

## Program close = two results

| Field | Meaning |
|-------|---------|
| **Program outcome** | A completed hire yields an employee with contracted identity and linked documents, and one status readable from both sides |
| **Release delta** | Minimal Recruitment → HR handoff four-checks PASS. Full HR operations stay later. If this is the last OPEN blocker, the [Release Readiness Gate](../gates/release-readiness-gate.md) may open — a program close still does **not** declare v1 ready |

---

## Queue position

**Depends on:** Hiring E2E program close (known acceptance edge: handoff acceptance needs a completed hire) + queue amendment
**Unlocks:** entry condition EC-1 of the Release Readiness Gate, if all other blockers are closed
**Does not:** schedule itself; open full HR operations; rebuild Documents; reopen E3 / E4; bind remaining D-series consumers

---

## Refs

- [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) — blocker 5; “Full HR operations … are later”
- [Acceptance suite RS-8](../journeys/release-readiness-acceptance-suite.md) — the proof this program must satisfy
- [Hiring workflow E2E](hiring-workflow-e2e.md) — predecessor that produces the completed hire
- [Documents E3](documents-platform-e3-first-consumer-bind.md) ✅ · [E4](documents-platform-e4-candidate-document-link.md) ✅ — Document Link SoT this program reuses
- [Requirement Policy Management](requirement-policy-management.md) — defines which documents are required
