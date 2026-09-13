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
2. **Authoritative transition only (no evaluate-side mint):**  
   `ready_to_create_employee=true` on a **read / evaluate** Formalize response **MUST NOT** create Employee.  
   Mint runs **only** on the authoritative Formalize **apply / complete** seam that records the transition into materialized Employee:

   ```text
   Formalize apply/complete → ready_to_create_employee=true → ensure Employee via handoff_from_candidate
   ```

   Forbidden:

   ```text
   Formalize evaluate / GET → ready_to_create_employee=true → mint
   ```

3. **Idempotency is handoff / employment-context scoped:**  
   Re-apply of the **same** handoff must return the **same** `employee_id`.  
   Gate must prove that another employment/handoff context cannot silently reuse an unsuitable Employee link merely because `candidate_id` matches — unless existing `handoff_from_candidate` already encodes that guarantee (then prove by test; **do not** invent a second mint authority).  
4. **Employee for start_allowed = this handoff’s Employee:** after mint, `employment_start_allowed.v1` must evaluate the Employee **linked to this handoff / employment case**, not an arbitrary Employee that happens to share the Candidate.  
5. **Do not** implement slice 4 enforcement in the same PR.  
6. **Do not** change HR frontend.  
7. **Do not** open Full Spine.  
8. ESO-5 changes, if any, must be **narrow** (e.g. tolerate pre-existing Employee) — not a semantic rewrite of Started; Confirm still does **not** require `start_allowed`.

---

## Proofs (gate must show)

- [x] Authoritative Formalize **apply/complete** with `ready_to_create_employee=true` → canonical Employee mint via `handoff_from_candidate`  
- [x] Formalize **evaluate** (or equivalent read) with `ready_to_create_employee=true` → **no** mint / no write side effect  
- [x] Repeat apply on the **same handoff** → same `employee_id` (idempotent)  
- [x] Cross-context safety: unsuitable reuse across distinct employment/handoff contexts is prevented **or** proven impossible by existing `handoff_from_candidate` semantics (test evidence)  
- [x] Operational context parity preserved (compose `ensure_hr_operational_context` as designed)  
- [x] `start_allowed` evaluate runs with the Employee **linked to this handoff**, **before** any ESO-5 physical confirm  
- [x] ESO-5 not rewritten beyond narrow necessity; Confirm still does **not** require `start_allowed` in this slice  
- [x] No new mint services / employee authorities in diff  
- [x] No HR UI file changes in diff  
- [x] Full Spine not claimed  

---

## Completion proof (strict)

```text
authoritative ESO-4 completion (apply/complete)
  → canonical idempotent mint for this employment/handoff context
  → Employee ↔ handoff linkage proven
  → start_allowed evaluate works on that employee_id before physical confirm
```

**PASS stops exactly at:** Employee exists before `start_allowed`.  
**No** ESO-5 semantic changes until slice 4.

---

## Implementation sequence (slice 2)

```text
ensure seam (authoritative apply only; evaluate = read-only)
  → compose handoff_from_candidate + handoff linkage + ensure_hr_operational_context
  → named mint-cutover gate proofs (incl. evaluate≠mint, linkage, start_allowed)
  → Formalize apply/complete caller wires ensure when ESO-4 Formalize is on tree
  → PASS stamp
  → STOP (do not open slice 3 in the same change)
```

**Caller contract (Formalize):** HTTP evaluate / empty-read Formalize calls pass `authoritative_apply=False`. Formalize **apply/complete** that records allow-create completion passes `authoritative_apply=True` and only then may mint when `ready_to_create_employee=true`.

**Canonical runtime seam on this tree:** `ensure_employee_after_formalize_apply` in `backend/app/services/employment_formalize_employee_ensure.py`.  
If `employment_formalize_orchestrator` is not yet merged onto the working tree, Formalize HTTP wire is deferred to the Formalize merge PR — it must call this seam with the locks above. Slice 2 PASS is the ensure seam + named gate; it does **not** require inventing a parallel Formalize stack on integration.

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
