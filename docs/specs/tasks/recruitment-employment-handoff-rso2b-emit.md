# RSO-2B — Emit `ready_for_employment.v1` on Transfer

**Status:** **PASS**  
**Phase class:** product  
**Opened:** 2026-09-13  
**PASS stamp:** 2026-09-13 · implementation under test `ab864e86` · named gate `rso2-emit-manifest-gate` **10 passed**  
**Parent:** [`recruitment-employment-handoff-rso2-cutover.md`](recruitment-employment-handoff-rso2-cutover.md)  
**Depends on:**  
- RSO-1 PASS: [`../architecture/ready-for-employment-contract.md`](../architecture/ready-for-employment-contract.md)  
- Boundary ownership **Accepted:** [`../architecture/recruitment-employment-boundary-ownership.md`](../architecture/recruitment-employment-boundary-ownership.md)  
- **RSO-2A CLOSED:** persist = RFE-only; compat = temporary read-shim; Vacancy/Employer REUSE(+proof)  
**Named gate (this slice):** `rso2-emit-manifest-gate`  
**Does not open:** RSO-2C · RSO-2D · RSO-2E · Slice 4 · Full Spine · new ACL product · Formalize  

> **Emit only.** On `create_handoff` (`destination=internal_hr`), assemble and persist a validated `ready_for_employment.v1` boundary manifest.  
> Do **not** auto-init Employment, drop Accept ritual, cut over HR UI reads, or remove the shim.

---

## PASS evidence

| Proof | Evidence |
|-------|----------|
| Gate | `rso2-emit-manifest-gate` **10 passed** @ `ab864e86` |
| Emit path | `create_handoff(internal_hr)` → assemble RFE → `validate_ready_for_employment_package_v1` → persist |
| Persist artifact | `CandidateHandoffSnapshot.payload` = **only** `ready_for_employment.v1` (manifest = sole persisted boundary artifact) |
| No Accept on create | `create_handoff` does **not** call `accept_handoff` / `apply_employment_accept_policy` / Employment init |
| Compat | temporary `handoff_manifest_compat` read-shim — **not SoT**; removal = RSO-2E |
| Current reads | live Person/Documents/Vacancy/Employer remain preferred; manifest = as-of / decisions / refs |
| Vacancy pre-mint | narrow ADAPT via handoff-lane target proof |
| Out of slice | RSO-2C · Slice 4 · Full Spine **not touched** |

**STOP.** Do **not** open RSO-2C in this stamp. Next code step = RSO-2C (separate brief/PR).

---

## Original Goal → Completion Proof

**Problem this slice must permanently remove:**  
Transfer still writes legacy `build_handoff_snapshot_payload_v1` as the persisted boundary artifact; `ready_for_employment.v1` is Accepted but not emitted on the real handoff path.

**Completion proof (named consumer):**

```text
create_handoff (internal_hr)
  → assemble manifest from REQUIRED_AT_TRANSFER + authoritative PASS_IF_KNOWN only
  → validate_ready_for_employment_package_v1 passes
  → CandidateHandoffSnapshot.payload = ready_for_employment.v1 only
  → contract_id discriminates the artifact
  → legacy readers use temporary read-shim (live for current; manifest for as-of)
  → named gate green
```

**False close (reject):** richer package via new Recruitment prompts; dual-write legacy+RFE; Accept/init side effects on create; consumer UI cutover claimed as 2B; permanent shim; Slice 4 / Full Spine; inventing envelope beyond Accepted RFE shape.

---

## Scope (in)

1. Assemble `ready_for_employment.v1` at Transfer from existing authorities / Accepted ownership matrix only.  
2. Call `validate_ready_for_employment_package_v1` **before** persist; fail Transfer if invalid.  
3. Persist **only** that package in `CandidateHandoffSnapshot.payload` (existing row; no parallel entity).  
4. Land **temporary deprecated read-shim** so legacy consumers keep working without dual-write (RSO-2A strategy — required for emit not to break HR).  
5. Manifest evidence = **refs/provenance** only (no document copies / no file bytes).  
6. Pre-mint Vacancy/Employer HR read proof (or narrow existing-access ADAPT) — RSO-2A criterion.  
7. Regression: `create_handoff` does **not** call `accept_handoff` / `apply_employment_accept_policy` / Employment side effects.

---

## Scope (out)

| Out | Owner later |
|-----|-------------|
| Employment auto-init / drop ritual Accept | **RSO-2C** |
| HR host live read-model cutover | **RSO-2D** |
| Delete compat shim | **RSO-2E** |
| New Recruitment questions to “fill” the package | **Forbidden** |
| Dual-write legacy snapshot + RFE | **Rejected (RSO-2A)** |
| Slice 4 / Full Spine / new ACL | **Closed** |

---

## Emit content lock (ownership matrix)

Emit **only**:

- **REQUIRED_AT_TRANSFER** (including identity/contacts **minimum**, not full profile)  
- **PASS_IF_KNOWN** when value is **authoritative canonical** (not recruiter note / preference / raw form answer)

Do **not** collect new facts solely to pad the package. Do **not** emit Employment-owned decisions (medical/BHP applicability, ZUS, contract basis unless already authoritative agreement, etc.).

---

## Execution locks

1. **Transport remains `CandidateHandoff`.**  
2. **Payload = RFE only** — `contract_id == "ready_for_employment.v1"` (Accepted shape; no new envelope).  
3. **Validate before persist.**  
4. **Shim:** may project legacy *shape*; **MUST NOT** project legacy *authority* (current values ← live Person/Docs/Vacancy/Employer; as-of ← manifest only when historical).  
5. **Shim is temporary** — removal is RSO-2E; do not treat shim as SoT.  
6. **No Employment init on create** — Transfer emit ≠ Accept execute.  
7. **No RSO-2C/D/E work** in the same PR as “nice to have.”  
8. **STOP after this slice PASS** — do not auto-open RSO-2C in the same change.

---

## PASS criteria (machine)

- [x] `create_handoff` internal_hr builds canonical `ready_for_employment.v1`  
- [x] `validate_ready_for_employment_package_v1` runs and passes **before** persist  
- [x] `CandidateHandoffSnapshot.payload` stores **only** that package (internal_hr)  
- [x] `contract_id` uniquely identifies the artifact  
- [x] Legacy consumers work **only** via temporary read-shim (no dual-write)  
- [x] Manifest documents = refs/provenance, not copies  
- [x] Operational Person/Vacancy/Employer current reads do **not** prefer manifest (shim live-first)  
- [x] Pre-mint HR read of target Vacancy: narrow existing-access **ADAPT** (`vacancy_is_handoff_target_for_hr_lane`)  
- [x] `create_handoff` does **not** call legacy Accept / Employment side effects  
- [x] RSO-2C / Slice 4 / Full Spine untouched  
- [x] Named gate `rso2-emit-manifest-gate` green (**10 passed**)  

---

## After machine PASS

1. **PASS stamped** on this brief.  
2. **STOP.** Do **not** open RSO-2C in the same change.  
3. Next separate brief/PR: RSO-2C (Employment `apply_employment_accept_policy` auto-init; drop ritual Accept as default).

---

## Implementation map

| Concern | Location |
|---------|----------|
| Assemble + validate | `backend/app/services/ready_for_employment_emit.py` |
| Persist internal_hr → RFE | `backend/app/services/handoff_snapshot.py` |
| Temporary read-shim | `backend/app/services/handoff_manifest_compat.py` |
| Shim consumers | `hr_handoff_profile_context.py`, `hr_inbox.py`, `hr_documents_queue.py` |
| Vacancy pre-mint ADAPT | `backend/app/api/v1/vacancies/router.py` |
| Resolve package from snapshot | `employment_accept_orchestrator.resolve_ready_for_employment_package` |
| Gate | `backend/tests/platform/test_rso2_emit_manifest_gate.py` |
