# Employment formalize

**Status:** **Accepted** (L2 contract — Employment Formalize Gate / ESO-4)  
**Date:** 2026-09-09  
**Trusted base:** `feat/eso3-employment-missing-resolution` @ `b99f4136` (stacks on ESO-3 → ESO-2 → ESO-1)  
**Related:** [`employment-missing-resolution.md`](employment-missing-resolution.md) · [`early-employability.md`](early-employability.md) · [`../tasks/employment-spine-orchestrator-v1.md`](../tasks/employment-spine-orchestrator-v1.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02**. Does not rewrite L0.

> This file is the **SoT** for Formalize after `ready_to_formalize`.  
> Machine copy: `employment_formalize.v1` in `backend/app/reference/employment_formalize.py`.  
> Runtime: `backend/app/services/employment_formalize_orchestrator.py`.  
> Gate tests: `backend/tests/platform/test_employment_formalize_gate.py`.  
> Not ESO-5 Started. Not an HR employee card. Not universal legalization checklist.

---

## Operator question (one)

Given a handoff that is **ready to formalize**, plus employment context and confirmed canonical facts/evidence, **which formal actions/documents are mandatory for this context**, and after resolving only what is still missing, is formalization **`formalization_complete` / `blocked` / `missing`** — and only then may HostFlow emit machine-verifiable **`ready_to_create_employee`**?

No second question is this contract. Actual Employee mint UX depth and Started (physical start) are later / adjacent; ESO-5 owns Started, not mere Employee existence.

---

## Three acceptance gates (bind every change)

1. **RSO does not know how to employ.** Formalize is Employment-owned.  
2. **ESO does not re-ask Recruitment.** Confirmed package facts/evidence are reused; known docs are not re-requested.  
3. **Operator does not service the boundary.** Only **current** missing formal items are shown — never a universal “just in case” checklist.

---

## Input / output (frozen)

### Input

| Input | Role |
|-------|------|
| `ready_to_formalize` precondition | From ESO-3 (`resolution_decision=ready_to_formalize`) or equivalent: ESO-2 `employable` on accepted handoff |
| Employment context | Country / position (drives required formal actions) |
| Canonical facts + evidence | Package + confirmed formal action acknowledgements |
| Formalize patch (apply) | Minimal confirmations / evidence for **current** missing formal items only |

### Output

`policy_id` MUST be `employment_formalize.v1`.

| Decision | Meaning |
|----------|---------|
| `formalization_complete` | All context/pathway-required formal items satisfied; **`ready_to_create_employee=true`** |
| `missing` | One or more required formal items still outstanding (active only) |
| `blocked` | Not ready to formalize, or hard blockers prevent formalize |
| `rejected_patch` | Empty/invalid patch when input required, or gate-2 reuse violation |

Every decision MUST include:

- `required_actions` — derived from context/pathway (not a static dump)  
- `active_missing` — only unsatisfied required items  
- `primary_item` — one next formal step when not complete  
- `ready_to_create_employee` — `true` **only** when `formalization_complete`  
- `employee_created=false` — ESO-4 freezes the **allow** threshold; it does **not** mint Employee or open an HR employee card  

### Checklist ban

ESO-4 **MUST NOT** emit a universal onboarding/legalization checklist. Required actions are computed from employment context + legal pathway (+ optional position). Already satisfied evidence/confirmations are omitted from `active_missing`.

### Determinism

Legal/formal decision is **LLM-OFF**. AI may extract docs elsewhere; it must not decide `formalization_complete` / `ready_to_create_employee`.

### Employee threshold

Creating an Employee is **forbidden** unless `ready_to_create_employee=true` (this contract). ESO-4 itself stops at the allow signal — it is not the HR employee card and not Started.

---

## Thin PL required-actions table (ESO-4)

Derived after unique pathway from ESO-2:

| Pathway | Required formal items (thin) | Satisfied when |
|---------|------------------------------|----------------|
| `pl_eu_eea_free_movement` | `confirm_employment_contract_basis` | Confirmed in formalize acknowledgements |
| `pl_eu_eea_free_movement` | `identity_facts_present` | Package already has citizenship + name (reuse; never re-ask if present) |
| `pl_third_country_work_authorization` | `work_authorization_evidence` | Package evidence already has work authorization (reuse) |
| `pl_third_country_work_authorization` | `confirm_employment_contract_basis` | Confirmed in formalize acknowledgements |

No other items appear on this thin table. Position may refine labels, not invent a universal pack.

---

## Write authority

| May | Must not |
|-----|----------|
| Derive required formal actions from context/pathway | Dump universal checklist |
| Resolve only active missing items; re-evaluate | Re-ask known/confirmed docs/facts without conflict |
| Emit `ready_to_create_employee` when complete | Create Employee / HR card / Started |
| Deterministic LLM-OFF formalize decision | Let AI set complete / allow-create |

---

## Non-goals

- ESO-5 Started (physical start / выход).  
- HR employee card / workforce profile chrome.  
- Actually inserting `workforce_employees` in this gate (allow signal only).  
- Full Legalization Engine.  
- Mapping Authority.  
- Recruitment Transfer calling this API.

---

## Completion of ESO-4

**PASS** when this document + `employment_formalize.v1` + gate tests exist, the ESO brief names Formalize, and HostFlow can answer **formalization_complete / blocked / missing** with context-derived required actions and emit **`ready_to_create_employee` only when complete** — without Employee create and without a universal checklist.
