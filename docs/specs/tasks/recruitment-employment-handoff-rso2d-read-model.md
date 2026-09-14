# RSO-2D — HR host read-model cutover

**Status:** **OPEN**  
**Phase class:** product  
**Opened:** 2026-09-13  
**Parent:** [`recruitment-employment-handoff-rso2-cutover.md`](recruitment-employment-handoff-rso2-cutover.md)  
**Depends on:**  
- RSO-1 PASS: [`../architecture/ready-for-employment-contract.md`](../architecture/ready-for-employment-contract.md)  
- Boundary ownership **Accepted:** [`../architecture/recruitment-employment-boundary-ownership.md`](../architecture/recruitment-employment-boundary-ownership.md) (lock 6)  
- **RSO-2A CLOSED** + **RSO-2B PASS** ([`recruitment-employment-handoff-rso2b-emit.md`](recruitment-employment-handoff-rso2b-emit.md) @ `ab864e86`)  
- **RSO-2C PASS** ([`recruitment-employment-handoff-rso2c-auto-init.md`](recruitment-employment-handoff-rso2c-auto-init.md) @ `5c9da75c`)  
**Named gate (this slice):** `rso2-read-model-gate`  
**Does not open:** RSO-2E · Slice 4 · Full Spine · new ACL product · Formalize · emit/init retouch  

> **Read-model only.** Cut over HR host operational reads so current values come from live authorities (Person / Documents Hub / Employer / Vacancy) and the manifest supplies Why Ready (fits / requirement verdicts / evidence refs) + as-of audit only.  
> Do **not** delete `handoff_manifest_compat` (RSO-2E). Do **not** retouch Transfer emit or Employment auto-init. Do **not** open Slice 4.

---

## Original Goal → Completion Proof

**Problem this slice must permanently remove:**  
HR host still reconstructs operational current-values through the temporary compat shim / legacy snapshot shape (name, contacts, citizenship, vacancy labels, document list for chips), even though live Person / Hub / entities already exist and Transfer already emits `ready_for_employment.v1`.

**Completion proof (named consumer):**

```text
HR opens /app/hr/handoffs/:id (post Transfer + auto-init)
  → header / inbox name ← live Person
  → contacts / citizenship (current) ← live Person
  → document verification files / statuses ← Document Hub
  → employer / vacancy (current) ← live entities by ref
  → Why Ready / fits / requirement verdicts / evidence refs ← manifest (backend why_ready)
  → as-of / transfer audit ← manifest only when historical
  → operational path does not call coerce_snapshot_payload_for_legacy_readers for current-values
  → named gate green
```

**False close (reject):** claiming cutover while inbox/profile/detail still prefer shim for current name/contacts/citizenship/docs; deleting the shim in this PR (that is 2E); retouching emit/Accept/init; treating manifest as current-value SoT (lock 6); FE aggregating Why Ready from snapshot; Slice 4 / Full Spine; new ACL.

---

## Scope (in)

1. **Inbox / detail display name** — `candidate_display_name` from **live Person**.  
2. **Verification profile column (current)** — live Person; no coerce for currents.  
3. **Documents (operational)** — Hub statuses; live name summaries.  
4. **Employer / Vacancy (current)** — live entities.  
5. **Why Ready surface** — backend `why_ready` from manifest; FE display-only.  
6. Named machine gate `rso2-read-model-gate`.  
7. Shim file remains until 2E.

---

## Scope (out)

| Out | Owner later |
|-----|-------------|
| Delete `handoff_manifest_compat` | **RSO-2E** |
| Slice 4 / Full Spine / new ACL | **Closed** |
| Retouch Transfer emit / Accept / auto-init | **Forbidden** (2B/2C closed) |
| Dual-write / permanent shim | **Forbidden** |
| FE Why Ready aggregation SoT | **Forbidden** |

---

## Execution locks

1. **Lock 6 (boundary):** never prefer manifest current-value over live Person / Hub / Vacancy / Employer.  
2. **Manifest role:** fits / verdicts / evidence refs / as-of audit / Why Ready only.  
3. **Why Ready SoT = backend read model** — FE must not reconstruct from raw snapshot.  
4. **Shim may remain on disk** until RSO-2E — operational host must not depend on it.  
5. **No emit/init changes.**  
6. **STOP after PASS** — do not auto-open 2E.

---

## PASS criteria (machine)

- [ ] Inbox `candidate_display_name` for RFE handoffs comes from **live Person**  
- [ ] HR verification profile **current** identity prefers **live Person** without `coerce_snapshot_payload_for_legacy_readers`  
- [ ] Document verification / queue operational statuses prefer **Hub**; names from live Person  
- [ ] Vacancy / employer current labels resolve from **live entities** when refs exist  
- [ ] Why Ready readable from **backend** `why_ready` (manifest-derived)  
- [ ] Operational helpers in `hr_inbox` / `hr_handoff_profile_context` / `hr_documents_queue` do **not** call coerce  
- [ ] `handoff_manifest_compat.py` still present  
- [ ] RSO-2B emit + RSO-2C auto-init regression green  
- [ ] Slice 4 / Full Spine / new ACL untouched  
- [ ] Named gate `rso2-read-model-gate` green  

---

## After machine PASS

1. **PASS stamped** on this brief with implementation SHA.  
2. **STOP.** Do **not** open RSO-2E in the same change.  
3. Next separate: RSO-2E delete compat shim + named cutover gate.

---

## Implementation map

| Concern | Location |
|---------|----------|
| Live + Why Ready read model | `backend/app/services/hr_handoff_read_model.py` |
| Inbox name / transfer_summary / why_ready | `backend/app/services/hr_inbox.py` + `api/v1/hr_inbox.py` |
| Verification profile namespace | `backend/app/services/hr_handoff_profile_context.py` |
| Documents queue / hub labels | `hr_documents_queue.py`, `hr_documents_hub.py` |
| FE Why Ready display (no reconstruction) | `HrHandoffContextSummary.tsx` |
| Temporary shim (keep until 2E) | `backend/app/services/handoff_manifest_compat.py` |
| Named gate | `backend/tests/platform/test_rso2_read_model_gate.py` |
| CI wire | `.github/workflows/backend-ci.yml` → `rso2-read-model-gate` |
