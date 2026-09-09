# Early employability

**Status:** **Accepted** (L2 contract — Early Employability Gate / ESO-2)  
**Date:** 2026-09-09  
**Trusted base:** `feat/eso1-employment-accept-policy` @ `38511932` (stacks on ESO-1; integration line remains RSO-1 tip until #353/#354 merge)  
**Related:** [`employment-accept-policy.md`](employment-accept-policy.md) (`employment_accept_policy.v1`) · [`ready-for-employment-contract.md`](ready-for-employment-contract.md) · [`../tasks/employment-spine-orchestrator-v1.md`](../tasks/employment-spine-orchestrator-v1.md) · [ADR-017](../../adr/ADR-017-work-eligibility-gates-zus.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (Employment owns employability). Does not rewrite L0. Does not mint Employee.

> This file is the **SoT** for Employment’s early employability evaluation after Accept / `employment_started`.  
> Machine copy: `early_employability.v1` in `backend/app/reference/early_employability.py`.  
> Runtime evaluate: `backend/app/services/early_employability_orchestrator.py` (read/evaluate only).  
> Gate tests: `backend/tests/platform/test_early_employability_gate.py`.  
> Not ESO-3 Formalize / Employee. Not ESO-4 Started. Not Recruitment. Not ADR-017 post-hire ZUS journey SoT.

---

## Operator question (one)

After Employment has accepted a handoff (`employment_started`), **can this transferred person be employed now in this employment context** — and if not, **what concrete blockers or missing facts** prevent the next decision — **without creating an Employee** and **without requiring the operator to know the internal legal model**?

No second question is this contract. Formalize / Employee create, confirm Started, and full Legalization Engine breadth are later slices.

---

## Three acceptance gates (bind every change)

1. **RSO does not know how to employ.** Employability is Employment-owned. Recruitment must not call employability evaluate as Transfer completion.  
2. **ESO does not re-ask Recruitment.** Canonical facts already on `ready_for_employment.v1` (person, citizenship, vacancy/employer, evidence refs) are **reused**. Missing prompts are **minimal employment facts/evidence** needed for the next decision only.  
3. **Operator does not service the boundary.** After Accept, the operator does **not** manually pick a legal pathway when it is uniquely determined from canonical facts + employment context.

Machine ids (shared): `rso_terminal_is_package` · `eso_reuses_package_no_reask` · `operator_does_not_service_boundary`.

---

## Input / output (frozen)

### Input

| Input | Role |
|-------|------|
| Accepted handoff | Precondition: status `accepted` (post ESO-1 / `employment_started`) |
| Employment context | Where/how Employment intends to employ (thin: `employment_country`, optional `position_category`) |
| Canonical facts | From validated `ready_for_employment.v1` (+ optional explicit overrides that must not re-ask package facts without `conflict_reason`) |

Evaluation is **deterministic** and **LLM-OFF**. AI may extract/propose facts elsewhere; it must **not** decide eligibility.

### Output

`policy_id` MUST be `early_employability.v1`.

| Decision | Meaning |
|----------|---------|
| `employable` | Facts + context suffice; pathway uniquely set (or N/A); Employment may proceed toward Formalize |
| `blocked` | Concrete employment blockers / requirements prevent employ-now; pathway still set when unique |
| `insufficient_facts` | Minimal missing fact/evidence needed for the **next** decision — not a universal checklist |

Every decision MUST include:

- `blockers` / `requirements` (concrete; empty when none)  
- exactly **one** `next_step` (`code` + `label`)  
- `legal_pathway` when uniquely determined (`pathway_id` + `selection_required=false`)  
- `employee_created=false` always (ESO-2 never creates Employee)

### Legal pathway lock

When canonical citizenship + employment context uniquely determine a pathway, the system **sets** `legal_pathway.pathway_id` and **MUST NOT** require operator pathway selection (`selection_required=false`).

Operator pathway choice is forbidden whenever uniqueness holds. Ambiguity is resolved by asking a **discriminating fact**, not by dumping a pathway menu — unless uniqueness truly cannot be restored from facts (out of thin ESO-2 PL scope).

### Requirements vs checklist

Employment requirements appear **only as a consequence** of the resolved employability context (country + pathway + optional position). ESO-2 must **not** emit a pre-collected universal legalization shopping list independent of that context.

---

## Thin PL pathway table (ESO-2)

For `employment_country=PL` (default when context omits country but package `target_work` is present):

| Citizenship group | Unique pathway_id | Typical next |
|-------------------|-------------------|--------------|
| EU / EEA / CH (ISO2) | `pl_eu_eea_free_movement` | `employable` → `proceed_to_formalize` |
| Third-country | `pl_third_country_work_authorization` | `employable` if work-authorization evidence present; else `blocked` / `insufficient_facts` for that evidence |
| Missing / invalid ISO2 | — | `insufficient_facts` → ask **citizenship** only |

`position_category=driver` may add contextual requirements (e.g. work-authorization evidence for third-country) — still not a universal checklist.

---

## Write authority

| May | Must not |
|-----|----------|
| Employment evaluate after accepted handoff | Create Employee / formalize |
| Set unique legal pathway from facts | Force operator pathway pick when unique |
| Return minimal missing fact/evidence | Re-ask package citizenship/employer/vacancy without `conflict_reason` |
| Deterministic LLM-OFF eligibility | Let AI decide employable/blocked |
| Surface contextual requirements | Emit universal always-on legalization checklist |

---

## Non-goals

- ESO-3 Employment Missing / Resolution — [`employment-missing-resolution.md`](employment-missing-resolution.md).  
- ESO-4 Formalize / Employee materialization.  
- ESO-5 Started — [`employment-started.md`](employment-started.md).  
- Full Legalization Engine / multi-jurisdiction pathway menus.  
- ADR-017 ZUS registration gate cutover (satellite; may consume pathway later).  
- Mapping Authority.  
- Recruitment Transfer calling this API.

---

## Completion of ESO-2

**PASS** when this document + `early_employability.v1` + gate tests exist, the ESO brief names early employability, and after `employment_started` HostFlow can answer **employable / blocked / insufficient_facts** with concrete blockers and one next step — **without** creating Employee and **without** requiring operator knowledge of the internal legal model.
