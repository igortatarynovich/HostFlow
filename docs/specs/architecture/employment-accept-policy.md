# Employment accept policy

**Status:** **Accepted** (L2 contract — Employment Accept Policy Gate / ESO-1)  
**Date:** 2026-09-09  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ready-for-employment-contract.md`](ready-for-employment-contract.md) (`ready_for_employment.v1`) · [`../tasks/employment-spine-orchestrator-v1.md`](../tasks/employment-spine-orchestrator-v1.md) · [`../tasks/recruitment-spine-orchestrator-v1.md`](../tasks/recruitment-spine-orchestrator-v1.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (Employment owns accept/employ) and the three RSO/ESO acceptance gates. Does not rewrite L0. Does not mint Employee from Recruitment.

> This file is the **SoT** for Employment’s accept policy after Recruitment emits `ready_for_employment.v1`.  
> Machine copy: `employment_accept_policy.v1` in `backend/app/reference/employment_accept_policy.py`.  
> Runtime apply: `backend/app/services/employment_accept_orchestrator.py` (calls existing `accept_handoff`).  
> Gate tests: `backend/tests/platform/test_employment_accept_policy_gate.py`.  
> Not ESO-2 employability SoT. Not formalize / Started. Not Recruitment Transfer.

---

## Operator question (one)

When Employment receives a validated Ready for employment package and a pending handoff, **under what policy** may Employment auto-accept and initialize — reusing package facts — without a ritual Accept screen and without re-asking Recruitment?

No second question is this contract. Employability pathway choice, formalize, Employee create policy depth, and Started are later ESO slices.

---

## Three acceptance gates (bind every change)

1. **RSO does not know how to employ.** Recruitment must not call Employment accept as its completion. Accept/init are Employment-owned.  
2. **ESO does not re-ask Recruitment.** Package-authoritative facts (person id, identity facts already used, vacancy/employer, recruitment facts, evidence refs) are **reused**. Additional prompts are **employment missing** only. Re-prompting package facts without a documented `conflict_reason` is a product FAIL.  
3. **Operator does not service the boundary.** After **Передать на трудоустройство**, when Employment gates pass, Accept/init are **internal** (auto). Ritual Accept is forbidden when the policy returns `auto_accept`.

Machine ids (shared with RFE contract): `rso_terminal_is_package` · `eso_reuses_package_no_reask` · `operator_does_not_service_boundary`.

---

## Write / accept authority

| May | Must not |
|-----|----------|
| Employment evaluates accept policy on a valid `ready_for_employment.v1` | Recruitment call `accept_handoff` as Transfer completion |
| Auto-accept when policy says `auto_accept` via existing `accept_handoff` | Re-ask citizenship / employer / vacancy / package evidence without conflict |
| Audit: **Employment started** after successful accept | Treat ritual Accept UI as the happy path when gates already pass |
| Return concrete **employment** blockers when not auto | Place package-authoritative codes into `employment_missing` without `conflict_reason` |

---

## Decision shape (frozen)

`policy_id` MUST be `employment_accept_policy.v1`.

| Decision | Meaning |
|----------|---------|
| `auto_accept` | Package valid; no Employment blockers for accept-init; call `accept_handoff`; audit Employment started |
| `review_required` | Concrete Employment blockers (or missing employment facts) — operator sees blockers, not a blank Accept ritual |
| `reject_invalid_package` | Package fails `ready_for_employment.v1` validation — do not accept |

### Package-authoritative field codes (must not re-ask)

`person`, `person_id`, `candidate_id`, `citizenship`, `nationality`, `first_name`, `last_name`, `vacancy_id`, `employer_id`, `target_work`, plus any key present under `recruitment_facts` / `evidence` already on the package.

An `employment_missing` row whose `field_code` is in that set **without** a non-empty `conflict_reason` is a gate 2 FAIL.

### ESO-1 accept-init blockers (thin)

For this gate, Employment blockers for accept are limited to:

- invalid / missing package  
- handoff not `pending_review`  
- tenant/destination policy forbid (e.g. internal HR disabled)  

Full employment-missing / legalization shopping lists are **ESO-2+**. ESO-1 may return `employment_missing: []` when auto-accepting.

---

## Delivery UX constraint (gate 3)

After Transfer, same person continues. When policy = `auto_accept`, no separate “Accept handoff” chore. When `review_required`, show **concrete blockers** only.

---

## Non-goals

- ESO-2 early employability SoT / pathway choice — **ESO-2:** [`early-employability.md`](early-employability.md).  
- ESO-3 formalize / Employee materialization policy depth beyond what `accept_handoff` already does.  
- ESO-4 Started.  
- Cutting over legacy handoff snapshot to `ready_for_employment.v1` storage (may read package from RSO prep or explicit payload).  
- Mapping Authority.  

---

## Completion of ESO-1

**PASS** when this document + `employment_accept_policy.v1` + gate tests exist, ESO brief names the accept policy, and apply path can auto-accept a valid package via `accept_handoff` without Recruitment calling it.
