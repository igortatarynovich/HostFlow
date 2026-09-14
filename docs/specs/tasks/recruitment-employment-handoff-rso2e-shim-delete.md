# RSO-2E — Delete compat shim + Manifest Cutover Gate

**Status:** **OPEN**  
**Phase class:** product  
**Opened:** 2026-09-14  
**Parent:** [`recruitment-employment-handoff-rso2-cutover.md`](recruitment-employment-handoff-rso2-cutover.md)  
**Depends on:**  
- **RSO-2D PASS** ([`recruitment-employment-handoff-rso2d-read-model.md`](recruitment-employment-handoff-rso2d-read-model.md) @ `aa0461d2`)  
- **RSO-2B PASS** ([`recruitment-employment-handoff-rso2b-emit.md`](recruitment-employment-handoff-rso2b-emit.md) @ `ab864e86`)  
- **RSO-2C PASS** ([`recruitment-employment-handoff-rso2c-auto-init.md`](recruitment-employment-handoff-rso2c-auto-init.md) @ `5c9da75c`)  
**Named gate (this slice):** `rso2-cutover-gate`  
**Does not open:** Slice 4 · Full Spine · new ACL product · Formalize · emit/init retouch  

> **Shim delete only.** Remove temporary `handoff_manifest_compat` and remaining operational reads of legacy snapshot *shape*.  
> Persist remains `ready_for_employment.v1` on `CandidateHandoffSnapshot.payload` for `internal_hr`.  
> Live currents stay on domain authorities; manifest stays Why Ready / as-of.  
> Do **not** open Slice 4.

---

## Original Goal → Completion Proof

**Problem this slice must permanently remove:**  
A temporary compat shim still exists as a possible runtime path from `ready_for_employment.v1` to legacy snapshot semantics, so RSO-2 cannot close (parent false close: eternal compatibility layer).

**Completion proof (named consumer):**

```text
HR host / inbox / verification profile / document queues
  → no import or call of handoff_manifest_compat / coerce_* / project_manifest_to_legacy_*
  → CandidateHandoffSnapshot.payload for internal_hr = ready_for_employment.v1 only
  → current identity/docs/vacancy/employer ← live authorities
  → Why Ready / fits / verdicts / evidence / as-of ← manifest (backend why_ready)
  → named rso2-cutover-gate green
  → RSO-2B / 2C / 2D gates still green
```

**False close (reject):** shim file gone but coerce copied into consumers; operational currents from `payload.candidate.*`; Slice 4 / Full Spine; retouching emit/Accept.

---

## Scope (in)

1. Delete `backend/app/services/handoff_manifest_compat.py`.  
2. Keep `contract_id` discriminator on the RFE reference contract (not a projection shim).  
3. HR inbox / profile / queue / hub operational paths: no legacy snapshot-shape projection for current values.  
4. Named final gate `rso2-cutover-gate`.  
5. Adjust 2B/2C/2D gates so they no longer require the shim file (emit/init/read-model proofs remain).

---

## Scope (out)

| Out | Owner later |
|-----|-------------|
| Slice 4 (`start_allowed` on Confirm) | **Closed — separate decision** |
| Full Spine / new ACL | **Closed** |
| Client-portal handoff snapshot v1 | **Out** (`internal_hr` only) |
| Retouch Transfer emit / Accept / auto-init | **Forbidden** |

---

## Execution locks

1. **No replacement shim.** Discriminator ≠ projection.  
2. **Lock 6:** manifest is not current-value SoT.  
3. **STOP after PASS** — do not auto-open Slice 4.  
4. Parent RSO-2 may then be treated as cutover-closed; Slice 4 remains a separate decision.

---

## PASS criteria (machine)

- [ ] `handoff_manifest_compat.py` does not exist  
- [ ] No `coerce_snapshot_payload_for_legacy_readers` / `project_manifest_to_legacy_snapshot_shape` in `backend/app`  
- [ ] Operational HR consumers do not project current identity from legacy `payload["candidate"]`  
- [ ] `internal_hr` persist path still writes RFE only  
- [ ] Why Ready still from `build_why_ready_from_manifest`  
- [ ] Named gate `rso2-cutover-gate` green  
- [ ] `rso2-emit-manifest-gate` / `rso2-auto-init-gate` / `rso2-read-model-gate` green  
- [ ] Slice 4 / Full Spine untouched  

---

## After machine PASS

1. **PASS stamped** with implementation SHA.  
2. **STOP.** Do not open Slice 4 in this change.  
3. Recruitment → Employment **boundary cutover** may be closed; Slice 4 is a separate decision.

---

## Implementation map

| Concern | Location |
|---------|----------|
| Discriminator | `backend/app/reference/ready_for_employment.py` |
| Deleted shim | `handoff_manifest_compat.py` |
| Live + Why Ready | `hr_handoff_read_model.py` |
| Inbox / profile / queue | `hr_inbox.py`, `hr_handoff_profile_context.py`, `hr_documents_queue.py` |
| Named gate | `backend/tests/platform/test_rso2_cutover_gate.py` |
| CI | `.github/workflows/backend-ci.yml` → `rso2-cutover-gate` |
