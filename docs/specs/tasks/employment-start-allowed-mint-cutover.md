# Employment start_allowed — mint timing cutover (slice 2)

**Status:** **OPEN** — mint timing only; not HR UI; not ESO-5 enforcement; not Full Spine  
**Phase class:** product  
**Opened:** 2026-09-13  
**Depends on:**  
- Slice 1 PASS: [`employment-start-allowed-runtime-foundation.md`](employment-start-allowed-runtime-foundation.md) @ `d5767488`  
- Adaptation design: [`../../analysis/employment-start-allowed-adaptation-design.md`](../../analysis/employment-start-allowed-adaptation-design.md) (**Accepted**)  
- Inventory: [`../../analysis/employment-start-allowed-runtime-inventory.md`](../../analysis/employment-start-allowed-runtime-inventory.md) @ `466016b6`  
**Named gate (this slice):** `employment-start-allowed-mint-cutover-gate` (or extend foundation gate with mint-timing proofs — choose one named gate, no duplicate SoT)  
**Does not amend:** L0 · ESO-4 Formalize thin table · Full Spine Gate · slice 3/4 scopes  

> **Slice 2 of 4.** Move Employee materialization to the correct moment: immediately after ESO-4 `ready_to_create_employee=true`, using **only** existing `handoff_from_candidate`.  
> Prepare `Employee exists` before `start_allowed`. **Do not** enforce `start_allowed` on ESO-5 here. **Do not** delete legacy mint-on-confirm (slice 4).

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Foundation evaluator requires `employee_id`, but Employment spine still may lack an Employee until ESO-5 physical confirm (legacy mint-on-confirm). That couples admit-to-work machinery to Started and blocks the Accepted order `ESO-4 → mint → start_allowed → ESO-5`.

**Completion proof (named consumer):**

```text
ESO-4 allow-create (ready_to_create_employee=true)
  → handoff_from_candidate
  → Employee exists
  → foundation evaluator can run on employee_id
  → without depending on ESO-5 physical confirm
```

Machine proofs (named gate green) must show the bullets in § Proofs. **No** HR host binding required for this slice PASS.

**False close (reject):** new mint service / `create_employee` as spine path; HR UI changes; requiring `start_allowed` inside ESO-5 confirm; deleting mint-on-confirm in this slice; Full Spine claim; rewriting Formalize thin table.

---

## In scope

1. **Canonical call site** after Formalize `ready_to_create_employee=true`: invoke existing `handoff_from_candidate` (idempotent).  
2. **Operational context parity** with accept-path composition where inventory required it — prefer existing `ensure_hr_operational_context` (compose helpers; do not fork mint).  
3. Ensure subsequent `employment_start_allowed.v1` evaluate receives a real `employee_id` without ESO-5 confirm.  
4. Named machine gate / proofs for this cutover.  
5. Minimal ESO-5 touch **only if required** so mint-at-confirm is not the *only* path to Employee for the Employment spine happy path — **without** making Confirm require `start_allowed` (slice 4).

## Out of scope (hard)

| Item | Belongs to |
|------|------------|
| HR UI / handoff panels for start_allowed | **Slice 3** |
| ESO-5 Confirm requires `start_allowed=true` | **Slice 4** |
| Remove / forbid PEM-1 mint-on-confirm | **Slice 4** |
| New mint primitive or employee authority | **Forbidden** |
| Documents evidence write paths | Slice 3 / Documents |
| Full Spine Gate | Later |

---

## Execution locks

1. **Only** `handoff_from_candidate` for Employment-spine mint after ESO-4. No new mint service. Manual `create_employee` stays out of happy path.  
2. **Idempotent:** second call with same candidate returns existing Employee; no duplicate rows.  
3. **Do not** implement slice 4 enforcement in the same PR.  
4. **Do not** change HR frontend.  
5. **Do not** open Full Spine.  
6. ESO-5 changes, if any, must be **narrow** (e.g. tolerate pre-existing Employee) — not a semantic rewrite of Started.

---

## Proofs (gate must show)

- [ ] `ready_to_create_employee=true` → canonical Employee mint via `handoff_from_candidate`  
- [ ] Repeat call idempotent (same `employee_id`)  
- [ ] Operational context parity preserved (HR case / links / review helpers as designed — no weaker mint than accept path without documented constraint)  
- [ ] `start_allowed` evaluate can run with existing `employee_id` **before** any ESO-5 physical confirm  
- [ ] ESO-5 not rewritten beyond narrow necessity; Confirm still does **not** require `start_allowed` in this slice  
- [ ] No new mint services / employee authorities in diff  
- [ ] No HR UI file changes in diff  
- [ ] Full Spine not claimed  

---

## Implementation sequence (slice 2)

```text
locate Formalize complete / allow-create runtime seam
  → compose handoff_from_candidate (+ operational context helpers)
  → wire employee_id into start_allowed evaluate inputs
  → named mint-cutover gate proofs
  → PASS stamp
  → STOP (do not open slice 3 in the same change)
```

---

## PASS criterion

After ESO-4 allow-create, Employee exists via `handoff_from_candidate` without ESO-5 physical confirm; foundation evaluator can use that `employee_id`; gate green; UI / Full Spine / slice-4 enforcement untouched.

**After PASS:** STOP before slice 3 HR binding.

---

## Non-goals

- Frontend Formalize / Started / start_allowed panels  
- `start_allowed` as ESO-5 precondition  
- Deleting legacy mint-on-confirm  
- Expanding ESO-4 Formalize requirements  
- ZUS / A1 / delegation  

---

## Next after slice 2 PASS

**STOP.** Then open **slice 3** (HR host binding) as a separate brief/PR. Slice 4 (ESO-5 enforcement + remove mint-on-confirm) remains later. Full Spine stays closed.
