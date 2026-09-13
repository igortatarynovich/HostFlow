# Employment start_allowed — mint timing cutover (slice 2)

**Status:** **PASS** — ESA2 **machine / portable ensure-seam** (not production Formalize-HTTP wired)  
**Phase class:** product  
**Opened:** 2026-09-13  
**PASS stamp:** 2026-09-13 · implementation under test `0c8b337f` · named gate `employment-start-allowed-mint-cutover-gate` **16 passed**  
**PASS class:** `ESA2 machine/portable seam PASS; integration wire pending ESO-4 line merge`  
**Depends on:**  
- Slice 1 PASS: [`employment-start-allowed-runtime-foundation.md`](employment-start-allowed-runtime-foundation.md) @ `d5767488`  
- Adaptation design: [`../../analysis/employment-start-allowed-adaptation-design.md`](../../analysis/employment-start-allowed-adaptation-design.md) (**Accepted**)  
- Inventory: [`../../analysis/employment-start-allowed-runtime-inventory.md`](../../analysis/employment-start-allowed-runtime-inventory.md) @ `466016b6`  
**Named gate (this slice):** `employment-start-allowed-mint-cutover-gate`  
**Does not amend:** L0 · ESO-4 Formalize thin table · Full Spine Gate · slice 3/4 scopes  

> **Slice 2 of 4.** Move Employee materialization to the correct moment: immediately after ESO-4 `ready_to_create_employee=true`, using **only** existing `handoff_from_candidate`.  
> Prepare `Employee exists` before `start_allowed`. **Do not** enforce `start_allowed` on ESO-5 here. **Do not** delete legacy mint-on-confirm (slice 4).

---

## PASS provenance (honest)

### Implementation under test

- **SHA:** `0c8b337f`  
- **Important:** `0c8b337f` is **not** a pure slice-2 commit. It also contains **candidate-missing WIP** (Recruitment card empty-state / recreate-from-application).  
- That does **not** cancel the machine PASS: `employment-start-allowed-mint-cutover-gate` proves ESA2 **in isolation**.  
- **candidate-missing WIP in the same SHA is explicitly excluded from ESA2 PASS scope** — do not treat the whole `0c8b337f` diff as ESA2.

### ESA2-relevant files / scope (in PASS)

| Path | Role |
|------|------|
| `backend/app/services/employment_formalize_employee_ensure.py` | Portable Formalize→Employee ensure seam |
| `backend/tests/platform/test_employment_start_allowed_mint_cutover_gate.py` | Named gate |
| `docs/specs/tasks/employment-start-allowed-mint-cutover.md` | This brief |
| `.github/workflows/backend-ci.yml` | CI job `employment-start-allowed-mint-cutover-gate` + `esa2` filter (paths limited to ESA2) |
| Existing compose targets (unchanged authority): `workforce_employees.handoff_from_candidate`, `workforce_hr_operational_context.ensure_hr_operational_context`, `employment_start_allowed.v1` evaluate | Mint + ops parity + start_allowed consumer |

### Explicitly out of ESA2 PASS scope (same SHA)

- All candidate-missing paths: `backend/app/api/v1/candidates/missing.py`, candidates router/schemas changes for missing/recreate, `test_candidate_missing_state.py`, `CandidateMissingPanel*`, `candidateMissing*`, CandidateCard missing UX, related i18n, candidates module-scope / candidates.md / RSO parent-link docs touches.  
- `hostflow-frontend/dummy-non-existing-folder/` — **never** part of ESA2; must not be committed.

### Gate evidence

- `employment-start-allowed-mint-cutover-gate`: **16 passed**  
- Authoritative apply (`authoritative_apply=True` + `ready_to_create_employee=True`) **writes** via `handoff_from_candidate`  
- Evaluate / read (`authoritative_apply=False`) **does not mint** / no write side effect  
- **Only** `handoff_from_candidate` (no new mint service / no `create_employee` spine path)  
- `meta.internal_hr_handoff_id` linkage proven for this handoff  
- `start_allowed` evaluate receives **that linked** Employee, not an arbitrary candidate Employee  
- Operational context parity via `ensure_hr_operational_context`  
- ESO-5 semantics / frontend / Confirm→`start_allowed` enforcement **untouched**  
- Full Spine **not** claimed  

### Integration wire status (not overclaimed)

- **Formalize HTTP wiring was not performed on this line:** ESO-4 Formalize orchestrator / HTTP are **absent** from `integration/release-product-a-b`.  
- Portable ensure-seam (`ensure_employee_after_formalize_apply`) is ready for **one call** when ESO-4 merges (`authoritative_apply` per caller contract below).  
- **Do not** describe this PASS as “slice 2 fully production-wired”.  

**Correct status:**  
`ESA2 machine/portable seam PASS; integration wire pending ESO-4 line merge.`

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Foundation evaluator requires `employee_id`, but Employment spine still may lack an Employee until ESO-5 physical confirm (legacy mint-on-confirm). That couples admit-to-work machinery to Started and blocks the Accepted order `ESO-4 → mint → start_allowed → ESO-5`.

**Completion proof (named consumer — machine / portable):**

```text
authoritative Formalize apply/complete seam (ensure_employee_after_formalize_apply)
  → ready_to_create_employee=true
  → handoff_from_candidate
  → Employee ↔ handoff linkage (meta.internal_hr_handoff_id)
  → foundation evaluator can run on that employee_id
  → without depending on ESO-5 physical confirm
```

Formalize **HTTP** production composition remains **pending** ESO-4 on this integration line.

**False close (reject):** claiming full production Formalize wire; new mint service / `create_employee` as spine path; HR UI / slice 3; requiring `start_allowed` inside ESO-5 confirm; deleting mint-on-confirm in this slice; Full Spine claim; rewriting Formalize thin table; treating candidate-missing files as ESA2.

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
| Formalize HTTP wire without ESO-4 on tree | **Pending ESO-4 merge** |
| Candidate-missing WIP | **Excluded from ESA2** |

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
- [x] No new mint services / employee authorities in ESA2 scope  
- [x] No HR start_allowed UI in ESA2 scope  
- [x] Full Spine not claimed  
- [x] Provenance: mixed SHA `0c8b337f` recorded; candidate-missing excluded from ESA2  
- [x] Formalize HTTP wire pending ESO-4 on integration (not overclaimed as production-wired)

---

## Completion proof (strict)

```text
authoritative ESO-4 completion (apply/complete)  [seam ready; HTTP wire pending ESO-4]
  → canonical idempotent mint for this employment/handoff context
  → Employee ↔ handoff linkage proven
  → start_allowed evaluate works on that employee_id before physical confirm
```

**PASS stops exactly at:** Employee exists before `start_allowed` **via portable ensure-seam**.  
**No** ESO-5 semantic changes until slice 4.  
**No** claim of full Formalize HTTP production wire on this integration line.

---

## Implementation sequence (slice 2) — done for machine PASS

```text
ensure seam (authoritative apply only; evaluate = read-only)     ✅
  → compose handoff_from_candidate + handoff linkage + ensure_hr_operational_context  ✅
  → named mint-cutover gate proofs (16 passed)                  ✅
  → Formalize HTTP caller wire when ESO-4 Formalize is on tree  ⏳ pending
  → PASS stamp (this section)                                   ✅
  → STOP                                                        ✅
```

**Caller contract (Formalize):** HTTP evaluate / empty-read Formalize calls pass `authoritative_apply=False`. Formalize **apply/complete** that records allow-create completion passes `authoritative_apply=True` and only then may mint when `ready_to_create_employee=true`.

**Canonical runtime seam:** `ensure_employee_after_formalize_apply` in `backend/app/services/employment_formalize_employee_ensure.py`.

---

## Non-goals

- Frontend Formalize / Started / start_allowed panels  
- `start_allowed` as ESO-5 precondition  
- Deleting legacy mint-on-confirm  
- Expanding ESO-4 Formalize requirements  
- ZUS / A1 / delegation  
- Claiming production Formalize HTTP wire without ESO-4 on tree  

---

## Integration parity PASS

**Status:** **PASS** — Formalize→ensure integration parity  
**PASS stamp:** 2026-09-13 · under test `322d0148` · gate `employment-formalize-ensure-integration-gate` **6 passed**  
**Does not open:** Slice 3 · Slice 4 · Full Spine  

Proven:

1. Formalize **apply** + ready → `ensure_employee_after_formalize_apply` (linked Employee)  
2. Formalize **evaluate/read** + ready → no mint / no write  
3. Handoff linkage (`employee_linked_handoff_id` / `meta.internal_hr_handoff_id`) preserved on repeat apply  

**STOP.** Slice 3 was closed until explicitly opened after this parity.

---

## Next after this PASS

**Integration wire:** done (`322d0148`). Integration parity: **PASS** (`8b3ef00c`). ESA2 portable seam PASS remains valid.

**Next:** [`employment-start-allowed-hr-host-binding.md`](employment-start-allowed-hr-host-binding.md) — **Slice 3 OPEN**.

Still locked until Slice 3 PASS then Slice 4:

- Full Spine = **NOT PASS**  
- mixed SHA `0c8b337f` is **not** a pure ESA2 diff  
- ignore `hostflow-frontend/dummy-non-existing-folder/`

Slice 4 and Full Spine remain later / closed. Do **not** implement Slice 4 in the Slice 3 PR.
