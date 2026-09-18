# RSO-2 — Recruitment → Employment handoff cutover

**Status:** **OPEN** (inventory + cutover brief — no implementation until inventory complete)  
**Phase class:** product  
**Opened:** 2026-09-13  
**Depends on:**  
- RSO-1 PASS: [`ready-for-employment-contract.md`](../architecture/ready-for-employment-contract.md) (`ready_for_employment.v1`)  
- Boundary ownership **Accepted:** [`recruitment-employment-boundary-ownership.md`](../architecture/recruitment-employment-boundary-ownership.md) (dual-axis)  
- Reality audit: [`../../analysis/recruitment-employment-handoff-reality-audit.md`](../../analysis/recruitment-employment-handoff-reality-audit.md)  
- ESO-1 Accepted: [`employment-accept-policy.md`](../architecture/employment-accept-policy.md)  
**Parent ladder:** [`recruitment-spine-orchestrator-v1.md`](recruitment-spine-orchestrator-v1.md)  
**Named gate (later):** Fits → Handoff / Manifest Cutover Gate (machine id TBD after inventory)  
**Does not open:** Slice 4 · Full Spine · new ACL/permission product · Formalize expansion  

> Cutover existing Transfer runtime from **legacy snapshot copies** to **immutable `ready_for_employment.v1` manifest + live shared authorities + access/scope transition + automatic `employment_accept_policy`**.  
> Keep `CandidateHandoff` as transport. Do not build a second handoff entity or HR dossier copy chain.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Operator Transfer still creates pending handoff + legacy `CandidateHandoffSnapshot` / employee snapshot copies; HR reconstructs the person after ritual Accept; `ready_for_employment.v1` is Accepted as contract but **not emitted**; Employment does not start from live Person/Documents + manifest decisions.

**Completion proof (named consumer):**

```text
Передать на трудоустройство
  → validate + emit ready_for_employment.v1 (boundary manifest)
  → Recruitment completed audit
  → CandidateHandoff transport + access/scope transition (reuse existing rules)
  → employment_accept_policy auto-evaluates
  → HR host opens: live Person + Target work + Why Ready (manifest)
       + live Documents/Evidence + first Employment-owned missing
  → no Take into HR review ritual when policy auto-accepts
  → no preferred UI read of manifest values when live authority exists
```

**False close (reject):** new permission engine without access inventory; second dossier; using manifest as current-value SoT; opening Slice 4; copying documents/files; treating recruiter notes as PASS_IF_KNOWN established facts.

---

## Cutover shape (locked by Accepted boundary)

```text
legacy snapshot writer
  → ready_for_employment.v1 manifest writer
  → access/scope transition (inventory-first)
  → automatic employment_accept_policy
  → HR host: manifest decisions + live Person/Documents/Employer/Vacancy
  → only Employment-owned missing
```

Not: Candidate copied → handoff copied → Employee copied → HR verifies copies.

---

## Execution locks

1. **Transport = existing `CandidateHandoff`.** Payload + init semantics change; no parallel handoff product.  
2. **Manifest ≠ live SoT.** Lock 6 from boundary ownership: operational UI defaults to live authorities.  
3. **Documents/Evidence = BOTH.** Immutable ref-set in manifest; same Hub objects live. Never copy files.  
4. **Identity/contacts = minimum REQUIRED;** other person facts PASS_IF_KNOWN only if authoritative.  
5. **Target role:** freeze target-work role ref/context when part of Recruitment context; if Vacancy alone is sufficient, do not duplicate.  
6. **Planned start / contract:** freeze only authoritative known; else Employment-owned.  
7. **Scope transition:** inventory existing tenant / entity / handoff / linkage access first; reuse if HR already gains access via accept/linkage. **No greenfield ACL subsystem by default.**  
8. **Do not** open Slice 4 or Full Spine in this brief.  
9. **Do not** implement until inventory section below is filled and cutover slices are sequenced.

---

## Inventory (must complete before feat code)

### A — Emit / package path

| Item | Current | Target | Notes |
|------|---------|--------|-------|
| Transfer operator action | `create_handoff` | same UX; emit manifest | |
| Legacy snapshot | `build_handoff_snapshot_payload_v1` | retire as SoT; replace/wrap with `ready_for_employment.v1` | |
| Validate API | `validate_ready_for_employment_package_v1` exists | call on emit | |
| Persist location | `candidate_handoff_snapshots.payload` | store manifest (or dedicated column) — decide in inventory | |

### B — Access / scope (inventory-first)

| Item | Current mechanism | Sufficient for HR after Transfer? | Reuse / adapt / new |
|------|-------------------|-----------------------------------|---------------------|
| Handoff create/accept ACL | | | |
| Document Hub HR access / `reused_for_hr` links | | | |
| Workforce employee linkage | | | |
| Recruitment write lock after handoff | | | |
| Tenant / company / module gates | | | |

**Decision rule:** if existing rules already give HR the needed reads after handoff/linkage, RSO-2 **reuses** them. New permission product only if inventory proves a hard gap.

### C — Employment init

| Item | Current | Target |
|------|---------|--------|
| Ritual Accept / pickup UI | present | remove as default when policy auto-accepts |
| `employment_accept_policy.v1` | Accepted + orchestrator | wire as automatic after manifest emit |
| Employee mint timing | accept / Formalize / delayed flag | preserve Employment ownership; align with Accepted boundary (no Recruitment mint) |
| HR host composition | snapshot + verification copies | live authorities + manifest decisions + Employment missing |

### D — Read model / UI

| Surface | Must read live | May show as-of from manifest |
|---------|----------------|------------------------------|
| Identity / citizenship / contacts | yes | audit only |
| Documents | Hub | ref-set provenance |
| Fits / requirements verdicts | — | yes (immutable) |
| Employer / vacancy | live entities | refs + labels as-of |
| First Employment missing | Employment SoT | — |

---

## Suggested internal ladder (after inventory)

| # | Slice | Outcome |
|---|-------|---------|
| **RSO-2A** | Access inventory + persist decision for manifest | Written inventory; reuse vs gap named |
| **RSO-2B** | Emit path: Transfer writes validated `ready_for_employment.v1` | Legacy snapshot no longer Transfer SoT |
| **RSO-2C** | Auto accept-policy + drop ritual Accept as default | Gate 3 operator path |
| **RSO-2D** | HR host: live + manifest decisions; lock 6 enforced | No preferred manifest current-value reads |
| **RSO-2E** | Named cutover gate + regression | Gate PASS |

Exact slice names may be adjusted after inventory; do not start RSO-2B before RSO-2A.

---

## Out of scope

- Slice 4 (`start_allowed` on Confirm)  
- Full Spine  
- New ACL product without inventory gap  
- Mapping Authority / Forms Publish  
- Expanding Recruitment to collect Employment lifecycle facts “just in case”

---

## Next

1. Complete **Inventory A–D** (docs PR or same brief update).  
2. Sequence RSO-2A…E with named gate.  
3. Only then feat PRs.  
4. Slice 4 stays closed until cutover proves Employment starts from live + manifest.
