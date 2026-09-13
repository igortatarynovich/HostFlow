# Employment start_allowed

**Status:** **OPEN** — architecture draft (L2 target); **STOP** — not Accepted; no runtime  
**Date:** 2026-09-13  
**Policy id (reserved):** `employment_start_allowed.v1` (not implemented)  
**Parent product decision:** [`../../analysis/production-employment-minimum.md`](../../analysis/production-employment-minimum.md) — **PEM-1 Accepted**  
**Baseline inventory:** [`../../analysis/employment-formalization-coverage-audit.md`](../../analysis/employment-formalization-coverage-audit.md) @ `b88a6168`  
**Adjacent contracts:** ESO-4 `employment_formalize.v1` (allow-create) · ESO-5 `employment_started.v1` (physical start)  
**Does not amend:** L0 · ESO-1…5 PASS stamps · Full Spine Gate  

> Seals the **pre-Start admit-to-work** authority for PEM-1.  
> **STOP:** do not implement code, HTTP, or UI until this document is **Accepted**.  
> **Do not** fold this into ESO-4. **Do not** auto-start from `start_allowed`.  
> **Do not** open Full Spine from this draft.

---

## Operator question (one)

Given an **Employee** already allowed / created (ESO-4 `ready_to_create_employee` satisfied), for PEM-1 context, **may this person be admitted to work** — i.e. is `start_allowed=true` — based only on proven Contract + Medical\* + BHP\* (or documented lawful exceptions), before any human Confirm physical start?

No second question is this contract. Physical start remains ESO-5. ZUS/Insurance remain post-Started lifecycle.

---

## Hard locks (from PEM-1 Accept)

| Lock | Meaning |
|------|---------|
| **ESO-4 stays thin** | Allow-create only. Do **not** add written-umowa proof, medical, or BHP to `employment_formalize.v1`. |
| **Employee ≠ admit-to-work** | Minting Employee does not imply `start_allowed`. |
| **`start_allowed` ≠ Started** | `start_allowed=true` does not emit physical start or auto-confirm ESO-5. |
| **ESO-5 requires `start_allowed`** | Confirm physical start is blocked unless `start_allowed=true` (PEM-1). |
| **ZUS not in this gate** | 7-day registration is lifecycle after Started — out of `start_allowed`. |
| **Context not checklist** | Medical\* / BHP\* model requirement vs lawful exception — no universal dump. |
| **LLM-OFF** | Admit-to-work decision is deterministic. |
| **PEM-1 scope** | A1 / delegacja / work-permit legalization **NOT REQUIRED** — must not appear as required_actions. |

---

## Placement in spine

```text
ESO-4 ready_to_create_employee
  → Employee exists
  → employment_start_allowed.v1  (THIS CONTRACT)
  → start_allowed=true
  → ESO-5 confirm_physical_start
  → Started
  → ZUS / Insurance deadline lifecycle
```

| Contract | Owns |
|----------|------|
| ESO-4 Formalize | Employee **creatable** |
| **start_allowed** | **Admit-to-work** (pre-Start) |
| ESO-5 Started | **Physical start** confirm |

---

## Input / output (draft — freeze on Accept)

### Input

| Input | Role |
|-------|------|
| Employee present (or creatable + mint in same apply — product choice later) | Precondition from ESO-4 path |
| PEM-1 employment context | PL employer, `umowa o pracę`, EU/EEA, domestic PL |
| Contract evidence | Written contract **or** written confirmation of parties / type / terms — or missing |
| Medical evidence\* | Valid occupational medical conclusion for **post + working conditions**, or documented exception |
| BHP evidence\* | Introductory BHP completed before admit, or documented exception (e.g. same employer / same post / immediately successive contract) |
| Resolution patch | Minimal evidence / exception acknowledgements for **active** missing items only |

### Output

`policy_id` MUST be `employment_start_allowed.v1` (when Accepted).

| Decision | Meaning |
|----------|---------|
| `start_allowed` | All PEM-1 pre-Start required items satisfied → ESO-5 may accept confirm |
| `missing` | One or more required pre-Start items outstanding (`active_missing` / one primary) |
| `blocked` | Preconditions fail (no Employee / not PEM-1 context / reuse violation) |
| `rejected_patch` | Empty/invalid patch when input required |

Every decision MUST include:

- `start_allowed` boolean (`true` only on decision `start_allowed`)  
- `required_actions` — derived for PEM-1 (Contract + Medical\* + BHP\*), not a universal pack  
- `active_missing` — unsatisfied only  
- `primary_item` — one next step when not allowed  
- `started=false` — this contract never sets Started  
- `employee_created` unchanged by admit decision (mint is not this gate’s job unless explicitly composed later)  
- `zus_required_for_start=false`  

### Checklist ban

MUST NOT emit A1, delegacja, legalization, ZUS registration, or insurance filing as `start_allowed` requirements for PEM-1.

---

## PEM-1 required-actions table (draft)

| Code (draft) | Kind | Satisfied when |
|--------------|------|----------------|
| `written_employment_contract_or_confirmation` | evidence | Evidence of written `umowa o pracę` **or** written confirmation of parties, type, and terms |
| `occupational_medical_fit_for_post` | evidence / exception | Valid medical conclusion for this post + conditions, **or** recorded lawful exception |
| `introductory_bhp_before_admit` | evidence / exception | Introductory BHP completed, **or** recorded lawful exception (same employer / same post / successive contract) |

Labels may refine; codes freeze on Accept. Position/context drives applicability of Medical\* / BHP\* — not a static dump on every Employee.

---

## Write authority

| May | Must not |
|-----|----------|
| Derive PEM-1 pre-Start required actions | Expand ESO-4 thin Formalize table |
| Resolve only active missing; re-evaluate | Re-ask known package facts without conflict |
| Emit `start_allowed=true` when complete | Set Started / auto Confirm physical start |
| Record exceptions as first-class evidence | Treat exception as silent skip without audit |
| Stay LLM-OFF | Let AI decide admit-to-work |

---

## Open questions (must close before Accept)

1. **Host & API shape** — evaluate/apply on handoff case vs employee id; composition with ESO-5 entry.  
2. **Evidence binding** — which document types / verified fields / operator attestations count as Contract / Medical / BHP proof.  
3. **Exception model** — schema for BHP successive-contract exception and any medical exceptions PEM-1 will honor.  
4. **Employee mint timing** — ESO-5 may mint today when allow-create; confirm mint stays before `start_allowed` evaluation (PEM-1 prefers Employee exists → start_allowed → confirm).  
5. **Named gate / CI** — whether a platform gate test is required before runtime (likely yes, mirror ESO-4/5).  
6. **Non-PEM-1** — explicit reject/blocked when pathway/geography is not PEM-1 (no silent fall-through).

Until these are answered in this file and Status → **Accepted**: **STOP** — no code.

---

## Non-goals

- Implementing runtime in this OPEN draft.  
- ZUS / Insurance in `start_allowed`.  
- A1 / posting / third-country.  
- Full Spine Gate.  
- Replacing ESO-5 human confirm.  
- ePUAP / Płatnik integrations.

---

## Completion of this architecture (Accept criteria)

**PASS / Accepted** when: operator question frozen; hard locks frozen; I/O + PEM-1 required-actions table frozen; open questions resolved; linkage from PEM-1 + ESO brief; named gate plan stated; **still no runtime required for Accept of the contract itself** (runtime is a later slice after Accept).

---

## Next

Resolve open questions → **Accept** this contract → only then schedule a thin runtime slice (reference + orchestrator + gate + HR host binding). Full Spine remains **NOT PASS** until PEM-1 `start_allowed` is proven in product.
