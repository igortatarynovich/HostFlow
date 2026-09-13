# Employment start_allowed — HR host binding (slice 3)

**Status:** **PASS** — HR host binding on existing `/app/hr/handoffs/:id`  
**Phase class:** product  
**Opened:** 2026-09-13  
**PASS stamp:** 2026-09-13 · implementation under test `cf68f150` · named gate `employment-start-allowed-hr-host-gate` **9 passed** (+ FE primaryWorkItem **2 passed**)  
**Depends on:**  
- Slice 1 PASS: [`employment-start-allowed-runtime-foundation.md`](employment-start-allowed-runtime-foundation.md) @ `d5767488`  
- Slice 2 portable PASS + Formalize→ensure integration parity PASS: [`employment-start-allowed-mint-cutover.md`](employment-start-allowed-mint-cutover.md) (under test `322d0148`; parity gate **6 passed**)  
- Architecture: [`../architecture/employment-start-allowed.md`](../architecture/employment-start-allowed.md) (**Accepted**)  
- Adaptation design: [`../../analysis/employment-start-allowed-adaptation-design.md`](../../analysis/employment-start-allowed-adaptation-design.md) (**Accepted**)  
**Named gate (this slice):** `employment-start-allowed-hr-host-gate`  
**Does not amend:** L0 · evidence authorities (Contract/Medical/BHP) · Formalize thin table · Full Spine Gate · slice 4 scope  

> **Slice 3 of 4.** Bind `employment_start_allowed.v1` onto the **existing** HR handoff host `/app/hr/handoffs/:id`.  
> Operator clears one active missing via existing evidence supply/bind or allowlisted exception → automatic re-evaluate → `start_allowed=true`.  
> **Do not** enforce on ESO-5 Confirm. **Do not** delete mint-on-confirm. **Do not** open Full Spine.

---

## PASS evidence

| Proof | Evidence |
|-------|----------|
| Host API | `POST /handoffs/{id}/employment-start-allowed` → `evaluate_start_allowed_for_handoff` / `apply_start_allowed_for_handoff` |
| UI host | `HrStartAllowedPanel` on `HrHandoffDetailPage` (no new route) |
| Primary only | `ui_primary_item` / `primaryWorkItem`; `active_missing` not rendered as checklist |
| No local evidence invent | apply rejects `upload` / `document` / `evidence_meta`; panel navigates to `#hr-document-verification` |
| Fresh re-eval | apply creates allowlisted exception then **re**-calls evaluate; panel sets state from response only |
| unsupported terminal | neutral copy; no Retry/Supply/override |
| No operator-set flag | reject `start_allowed` / `force_start_allowed` / `allow_anyway` |
| Gate | `employment-start-allowed-hr-host-gate` **9 passed** |

**PASS criterion (met):** On the existing handoff host, operator services only evaluator **`primary_item`**; every change goes through existing Documents navigation or typed exception authority; frontend has **no** own admit-to-work logic.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Machine `start_allowed` exists and Employee can exist before Confirm, but the HR operator has no host-bound surface to see the one active missing item, supply/bind evidence or an allowlisted exception, and get an automatic re-evaluate to `start_allowed=true` on the existing handoff case.

**Proven chain already in place (prerequisite — not this slice’s work):**

```text
ESO-4 authoritative apply
  → ready_to_create_employee
  → ensure_employee_after_formalize_apply
  → canonical linked Employee
  → employment_start_allowed.v1 can evaluate on the correct employee_id
```

**Completion proof (named consumer — this slice):**

```text
Employee exists (linked to this handoff)
  → evaluate start_allowed on /app/hr/handoffs/:id
  → UI shows exactly primary_item (evaluator order)
  → supply/bind via existing evidence authority OR allowlisted exception
  → authority write confirmed → fresh evaluate
  → next primary_item | start_allowed=true
```

PEM-1 progression example (order owned by evaluator, not frontend):

```text
Contract missing → resolve → Medical missing → resolve → BHP missing/allowlisted exception → resolve → start_allowed=true
```

**False close (reject):** new HR workflow/host; Start Allowed–local upload/editor; optimistic clear of missing without re-eval; treating `unsupported_context` as a human blocker with Retry/Supply/override; changing Contract/Medical/BHP evidence authorities; operator-set `start_allowed` PATCH; ESO-5 requires `start_allowed`; deleting mint-on-confirm; physical start / Started; Full Spine claim; expanding Formalize; rendering full `active_missing` as a UI checklist.

---

## Execution locks

1. **Host = existing handoff case only:** `/app/hr/handoffs/:id`. No parallel admit-to-work workflow.  
2. **Authority = Employee:** linked handoff Employee (ESA2 linkage).  
3. **Derived state only:** no PATCH `employee.start_allowed` / `force_start_allowed` / “Allow anyway”.  
4. **One active missing = UI primary only:** evaluator may return full `active_missing` for machine/audit; UI shows **exactly `primary_item`**. Order is evaluator-owned.  
5. **Evidence supply ≠ evidence creation inside start_allowed:** navigate/open existing Documents/bind only; **no** local upload/metadata editor in Start Allowed.  
6. **Automatic re-evaluate only after confirmed authority write:**

   ```text
   authority write/bind succeeds → evaluator rereads SoT → new decision
   ```

7. **`unsupported_context` is a neutral terminal** — no Retry / Supply / override.  
8. **Exceptions:** allowlisted typed exceptions only.  
9. **Do not** implement slice 4 in the same PR.  
10. **Do not** open Full Spine.  
11. **Do not** change Formalize mint / ESO-5 Confirm semantics.

---

## Proofs (gate must show)

- [x] Evaluate on host for linked Employee  
- [x] UI exposes exactly `primary_item`  
- [x] Evidence path = existing Documents navigate — no Start Allowed upload  
- [x] Confirmed exception write → fresh evaluate  
- [x] `unsupported_context` neutral terminal  
- [x] No invent-via-UI / no operator-set `start_allowed`  
- [x] No new HR host route  
- [x] Frontend has no own admit-to-work logic  
- [x] ESO-5 Confirm / mint-on-confirm / Full Spine untouched  

---

## Next after this PASS

**STOP.** Do **not** open Slice 4 or Full Spine automatically.

```text
Handoff Reality Audit
  → Boundary Ownership decision (REQUIRED_AT_TRANSFER / PASS_IF_KNOWN / EMPLOYMENT_OWNED)
  → after Accept: RSO-2 cutover (CandidateHandoff → ready_for_employment.v1 + auto-init)
  → only then Slice 4 (or narrower boundary fix if decision says so)
```

- Reality audit: [`../../analysis/recruitment-employment-handoff-reality-audit.md`](../../analysis/recruitment-employment-handoff-reality-audit.md)  
- Ownership decision (**Proposed**): [`../architecture/recruitment-employment-boundary-ownership.md`](../architecture/recruitment-employment-boundary-ownership.md)  
- Do **not** open RSO-2 or Slice 4 until that decision is Accepted.
