# Employment missing resolution

**Status:** **Accepted** (L2 contract — Employment Missing / Resolution Gate / ESO-3)  
**Date:** 2026-09-09  
**Trusted base:** `feat/eso2-early-employability` @ `9060d402` (stacks on ESO-2 → ESO-1)  
**Related:** [`early-employability.md`](early-employability.md) (`early_employability.v1`) · [`employment-accept-policy.md`](employment-accept-policy.md) · [`../tasks/employment-spine-orchestrator-v1.md`](../tasks/employment-spine-orchestrator-v1.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02**. Does not rewrite L0. Does not mint Employee.

> This file is the **SoT** for turning an ESO-2 employability result into a **minimal executable resolution path**.  
> Machine copy: `employment_missing_resolution.v1` in `backend/app/reference/employment_missing_resolution.py`.  
> Runtime: `backend/app/services/employment_missing_resolution_orchestrator.py`.  
> Gate tests: `backend/tests/platform/test_employment_missing_resolution_gate.py`.  
> Not Formalize / Employee. Not ESO-4 Started. Not a second “evaluate the person” SoT — ESO-2 remains the eligibility evaluator.

---

## Operator question (one)

Given the latest early-employability decision (`employable` / `blocked` / `insufficient_facts`), **what is the minimal fact, evidence, or action the operator must supply next**, and after supplying it, **what is the updated employability outcome** — without showing a full legal checklist and without creating an Employee?

No second question is this contract. Formalize / Employee / Started are later slices.

---

## Three acceptance gates (bind every change)

1. **RSO does not know how to employ.** Resolution is Employment-owned. Recruitment must not call this as Transfer completion.  
2. **ESO does not re-ask Recruitment.** Patches must not re-prompt package-authoritative facts without `conflict_reason`.  
3. **Operator does not service the boundary.** UI shows **only what currently blocks progress** (from latest ESO-2 `next_step` / blockers / requirements). After a successful patch, HostFlow **automatically re-evaluates** employability — no ritual “re-check” chore.

---

## Input / output (frozen)

### Input

| Input | Role |
|-------|------|
| Accepted handoff + package + employment context | Same spine inputs as ESO-2 |
| Latest ESO-2 decision (or equivalent re-eval) | Source of active blockers / next_step |
| Resolution patch (optional on apply) | Minimal `facts` / `evidence` / `actions` to clear the **current** gap |

### Output

`policy_id` MUST be `employment_missing_resolution.v1`.

| Field | Meaning |
|-------|---------|
| `active_items` | Only items that **currently** block progress (derived from ESO-2 blockers/requirements + `next_step`). Not a universal legalization checklist. |
| `primary_item` | Exactly one current actionable item (from `next_step`) when not ready |
| `resolution_decision` | `ready_to_formalize` · `awaiting_input` · `still_blocked` · `rejected_patch` |
| `employability` | Full re-eval result after merge (`early_employability.v1`) |
| `employee_created` | Always `false` |

### Resolution decisions

| Decision | Meaning |
|----------|---------|
| `ready_to_formalize` | Re-eval = `employable`; Formalize is the next product boundary (still no Employee here) |
| `awaiting_input` | Re-eval = `insufficient_facts` (or employable-path gap); show only current active items |
| `still_blocked` | Re-eval = `blocked` with concrete blockers |
| `rejected_patch` | Patch empty when input required, or gate-2 reuse violation / invalid merge |

### Checklist ban

ESO-3 **MUST NOT** emit a static full legal checklist independent of the current employability context. `active_items` is always a projection of the **latest** ESO-2 blockers/requirements/next_step after (re-)evaluation.

### Auto re-evaluate lock

On successful patch apply, HostFlow **must** re-run `evaluate_early_employability_v1` on the merged package. The operator does not manually trigger a separate “recalculate eligibility” step as the happy path.

---

## Thin apply semantics

1. Start from current package (+ optional explicit package).  
2. Merge resolution patch into a **copy**: `facts` → `person.identity_facts` / top-level identity; `evidence` → `evidence` keys.  
3. Re-evaluate early employability.  
4. Rebuild `active_items` / `primary_item` from that result only.  
5. Never create Employee; never call Formalize.

---

## Write authority

| May | Must not |
|-----|----------|
| Merge minimal fact/evidence for current gap | Emit universal legalization checklist |
| Auto re-eval employability after patch | Create Employee / Formalize |
| Surface only current active blockers | Re-ask package facts without `conflict_reason` |
| Stop at `ready_to_formalize` | Treat Formalize as in-scope of this gate |

---

## Non-goals

- ESO-4 Formalize / `ready_to_create_employee` — [`employment-formalize.md`](employment-formalize.md).  
- ESO-5 Started.  
- Full Legalization Engine.  
- Replacing `early_employability.v1` as eligibility SoT.  
- Mapping Authority.  
- Recruitment Transfer calling this API.

---

## Completion of ESO-3

**PASS** when this document + `employment_missing_resolution.v1` + gate tests exist, the ESO brief names Missing / Resolution, and HostFlow can take blocker → minimal patch → auto re-eval → `ready_to_formalize` or updated active items — **without** Employee create and **without** a full legal checklist.
