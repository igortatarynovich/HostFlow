# RSO-2 — Recruitment → Employment handoff cutover

**Status:** **PASS** — RSO-2A docs **CLOSED**; **RSO-2B PASS**; **RSO-2C PASS**; **RSO-2D PASS**; **RSO-2E PASS** ([`recruitment-employment-handoff-rso2e-shim-delete.md`](recruitment-employment-handoff-rso2e-shim-delete.md) @ `909ce8a5`); boundary cutover **closed**; boundary E2E **PASS** ([`recruitment-employment-handoff-boundary-e2e-proof.md`](recruitment-employment-handoff-boundary-e2e-proof.md) · handoff `e9ef16f2-1ab6-49d0-91dd-aa7676995081`); Slice 4 **PASS** ([`employment-start-allowed-eso5-enforcement.md`](employment-start-allowed-eso5-enforcement.md) @ `b8c9dd04`); **STOP** — Full Spine still a separate decision  
**Phase class:** product  
**Opened:** 2026-09-13  
**Inventory stamp:** 2026-09-13 (runtime read-only)  
**RSO-2A closed:** 2026-09-13 — persist = RFE-only; compat = temporary read-shim  
**RSO-2B PASS:** 2026-09-13 · under test `ab864e86` · `rso2-emit-manifest-gate` **10 passed**  
**RSO-2C PASS:** 2026-09-13 · under test `5c9da75c` · `rso2-auto-init-gate` **7 passed**  
**RSO-2D PASS:** 2026-09-13 · under test `aa0461d2` · `rso2-read-model-gate` **9 passed**  
**RSO-2E PASS:** 2026-09-14 · under test `909ce8a5` · `rso2-cutover-gate` **10 passed** · combined 2B–2E **33 passed** · STOP before Slice 4  
**Depends on:**  
- RSO-1 PASS: [`ready-for-employment-contract.md`](../architecture/ready-for-employment-contract.md) (`ready_for_employment.v1`)  
- Boundary ownership **Accepted:** [`recruitment-employment-boundary-ownership.md`](../architecture/recruitment-employment-boundary-ownership.md) (dual-axis)  
- Reality audit: [`../../analysis/recruitment-employment-handoff-reality-audit.md`](../../analysis/recruitment-employment-handoff-reality-audit.md)  
- ESO-1 Accepted: [`employment-accept-policy.md`](../architecture/employment-accept-policy.md)  
**Parent ladder:** [`recruitment-spine-orchestrator-v1.md`](recruitment-spine-orchestrator-v1.md)  
**Named gate (later):** Fits → Handoff / Manifest Cutover Gate (machine id TBD)  
**Does not open:** Slice 4 · Full Spine · new ACL/permission product · Formalize expansion  

> Cutover existing Transfer runtime from **legacy snapshot copies** to **immutable `ready_for_employment.v1` manifest + live shared authorities + reuse of existing handoff-lane access + Employment-owned auto-init**.  
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
  → CandidateHandoff transport (existing handoff-lane access already opens HR reads)
  → Employment apply_employment_accept_policy (Employment-owned; not inside create_handoff)
  → HR host opens: live Person + Target work + Why Ready (manifest)
       + live Documents/Evidence + first Employment-owned missing
  → no Take into HR review ritual when policy auto-accepts
  → no preferred UI read of manifest values when live authority exists
```

**False close (reject):** Transfer synchronously runs legacy `accept_handoff` insides Recruitment create; new permission engine without gap; second dossier; using manifest as current-value SoT; opening Slice 4; copying documents/files.

---

## Cutover shape (locked)

```text
legacy snapshot writer
  → ready_for_employment.v1 manifest writer
  → (access already via CandidateHandoff internal_hr lane — inventory B)
  → Employment policy decides → Employment initializer (accept_handoff side effects)
  → HR host: manifest decisions + live Person/Documents/Employer/Vacancy
  → only Employment-owned missing
```

**Not:**

```text
Transfer emits → Recruitment internally calls legacy Accept
Candidate copied → handoff copied → Employee copied → HR verifies copies
```

---

## Execution locks

1. **Transport = existing `CandidateHandoff`.** Payload + init semantics change; no parallel handoff product.  
2. **Manifest ≠ live SoT.** Operational UI defaults to live authorities (boundary lock 6).  
3. **Documents/Evidence = BOTH.** Immutable ref-set in manifest; same Hub objects live. Never copy files.  
4. **Identity/contacts = minimum REQUIRED;** other person facts PASS_IF_KNOWN only if authoritative.  
5. **Target role:** freeze target-work role ref/context when part of Recruitment context; if Vacancy alone is sufficient, do not duplicate.  
6. **Planned start / contract:** freeze only authoritative known; else Employment-owned.  
7. **No greenfield ACL.** Inventory B: existing handoff lane already grants HR Candidate/Documents read **before Employee mint**. Reuse; do not invent a permission subsystem.  
8. **Transfer emit ≠ Accept execute.**  
   `create_handoff` may emit manifest and leave pending transport.  
   **Employment** `apply_employment_accept_policy` (post-Transfer, Employment-owned, idempotent initializer path) decides and then runs Employment side effects via `accept_handoff`.  
   Do **not** inline legacy Accept side effects inside Recruitment Transfer.  
9. **Do not** open Slice 4 or Full Spine in this brief.  
10. **RSO-2A closed:** persist RFE-only + temporary read-shim (see below). RSO-2B may start.  
11. **Compat projection may reproduce legacy *shape*, but MUST NOT reproduce legacy *authority* semantics.** Live current values always come from domain authorities; manifest supplies historical/as-of only when the consumer explicitly asks.  
12. **Final RSO-2 PASS includes removing the compat shim** (RSO-2E). A permanent compatibility layer is a false close.

---

## RSO-2A — Persist / read compatibility (**CLOSED**)

### Five-line decision

1. **Canonical persisted boundary artifact:** `ready_for_employment.v1` (existing RSO-1 shape; `contract_id` required — no new envelope).  
2. **Persistence:** existing `CandidateHandoffSnapshot.payload` only — **no** parallel manifest entity, **no** second JSON copy beside RFE.  
3. **Legacy compatibility:** **read-time shim only**, explicitly temporary / deprecated — builds `legacy-shaped read namespace` from `ready_for_employment.v1` + **live** authorities; never a write authority; never persisted back.  
4. **Live current values:** always Person / Documents / Vacancy / Employer domain authorities — **never** prefer manifest projection for “current”.  
5. **Vacancy/Employer access:** **REUSE** existing handoff-lane + entity refs if pre-mint proof passes; otherwise **narrow ADAPT** of existing rules only — never a new permission product.

### Why not dual-write / consumer-first

| Option | Rejected because |
|--------|------------------|
| Dual-write (legacy + RFE) | Two frozen Transfer representations → which is canonical? |
| Consumer-first | Blocks RSO-2B behind a large UI/verification refactor |
| **Read-shim (chosen)** | Matches manifest ≠ live SoT; one persisted SoT; unblocks emit |

### Temporary read model

```text
Persist once     → ready_for_employment.v1  (contract_id discriminates vs any residual legacy rows)
Operational reads → Person / Documents / Vacancy / Employer  (live)
Historical reads → fits / requirement verdicts / evidence refs / transfer audit  (manifest)
Legacy consumers → compat_projection(manifest, live authorities)  [temporary, deprecated]
```

**Shim citizenship example:** current citizenship ← **live Person**; citizenship-at-transfer ← **manifest** only for explicit historical/as-of consumers. Do not substitute frozen UA into “current” just to keep an old API happy.

### Manifest identity

Use the **existing** RFE top-level `contract_id = "ready_for_employment.v1"` (and the rest of the Accepted package shape). Do **not** invent a wrapping envelope unless RSO-1 is amended. Readers discriminate: `contract_id == ready_for_employment.v1` → manifest; absence / other → treat as residual legacy (migration window only).

### Vacancy / Employer access proof (must pass in RSO-2A feat / test before calling REUSE closed in CI)

```text
pending internal_hr handoff
  → HR workspace actor (no Employee yet)
  → can READ target Vacancy + Employer referenced by the manifest / handoff application context
```

| Result | Action |
|--------|--------|
| PASS | **REUSE** — no new ACL |
| FAIL | **ADAPT** existing access rule narrowly; still not a new permission product |

Docs stance until proof runs: **REUSE intended**; proof is RSO-2A implementation acceptance criterion (not a reason to reopen dual-write).

### Rejected for RSO-2A

- Second persisted legacy snapshot alongside RFE  
- Permanent compat layer  
- New ACL/permission subsystem  
- New envelope schema beyond Accepted `ready_for_employment.v1`  

---

## Inventory verdict (2026-09-13)

| Area | Verdict |
|------|---------|
| **A Emit** | **RSO-2A CLOSED:** RFE-only persist + temporary read-shim |  
| **B Access** | **Reuse.** No new permission product for Person/Documents; Vacancy/Employer REUSE pending pre-mint proof |  
| **C Init** | **Split locked.** Policy decide ≠ Accept button; side effects on Employment initializer |  
| **D UI** | **Hybrid today.** Cutover in 2D; shim removed in 2E |

---

## B — Access / scope (critical — filled first)

### Moments

| Moment | Person / Candidate | Documents (candidate API / Hub) | Vacancy / Employer | Recruitment application | Workforce Employee | `/hr/handoffs/:id` |
|--------|--------------------|----------------------------------|--------------------|-------------------------|--------------------|--------------------|
| **1. Before Transfer** | HR: **no** (empty candidate ACL). Recruiter: yes | HR blocked via `ensure_candidate_access` | Tenant trust APIs (no HR-specific gate found) | HR blocked | none | no row |
| **2. After `create_handoff` (`pending_review`)** — **before Accept / mint** | HR: **yes by id** via `agency_candidate_has_internal_hr_handoff_lane` (includes `pending_review`). List discovery still empty | HR: **yes** same lane (`list_candidate_documents` → `ensure_candidate_access`). Hub employee-context UI: **no rows yet**. Snapshot embeds doc metadata | Snapshot title/id + tenant APIs | Readable if candidate access; status → `ready_for_handoff` | **none** (PR-4) | **yes** — module `hr` + handoff row + embedded snapshot; queue `awaiting_hr_pickup` |
| **3. After Accept / policy apply** | Same lane (`accepted`); stage → `processing_by_hr`; recruiter still write-locked | Candidate docs: yes. `document_entity_links` `reused_for_hr` created (→ review **or** employee). Doc queues include accepted | unchanged | → `handed_off` | Delayed OFF: mint. Delayed ON: still none until approve | accepted inbox; review ids |
| **4. After Employee mint** | Lane + `employee.candidate_id` | Hub contexts + links to `workforce_employee` | may copy ids onto employee | closed intent | workforce APIs | full row with `workforce_employee_id` |

### Mechanisms (evidence)

| Mechanism | What it does | New ACL needed? |
|-----------|--------------|-----------------|
| `agency_candidate_has_internal_hr_handoff_lane` + `ensure_candidate_access` | Widens HR single-candidate + documents access when internal_hr handoff active (`pending_review`+) | **No — reuse** |
| `require_hr_workforce_module_access` / company HR enablement | Module + company gates for inbox / workforce / accept-policy | **No — reuse** |
| Tenant RLS `app.tenant_id` | Isolation | **No — reuse** |
| Recruiter write lock (`is_recruitment_recruiter_write_locked_by_handoff`) | Limits Recruitment write after Transfer | **No — reuse** (lifecycle write-scope) |
| `document_entity_links` `reused_for_hr` | Created on **Accept**, not on create — improves Hub/employee surfaces; **not** required for pre-mint Candidate doc read | Adapt timing only if needed; not a new permission product |
| Employee linkage | Enrichment after mint; **not** the gate for initial HR Person/Doc read | **No** for Transfer access |

### B conclusion

**Existing `CandidateHandoff` (internal_hr) + tenant + HR module + handoff-lane ACL already solves HR read of Person/Documents before Employee mint.**  
Transfer does **not** need a new “permission handoff” subsystem. Process state change + manifest emit is enough for access; Employee mint remains Employment init, not an access prerequisite.

**Residual gaps (not new ACL):** HR candidate **list** stays empty (discovery via inbox only) — product OK for handoff host. Vacancy/Employer company-scoped HR narrowing: **UNKNOWN** beyond tenant trust — verify in RSO-2A if UI needs live vacancy beyond snapshot labels.

---

## A — Emit / package (filled)

| Item | Current | Finding | Target decision |
|------|---------|---------|-----------------|
| Transfer action | `create_handoff` | Only writer of snapshot (`persist_handoff_create_snapshot` ×2) | Keep UX; emit validated RFE |
| Legacy payload | `build_handoff_snapshot_payload_v1` | Keys: `handoff`, `candidate`, `application`, `documents`, `expected_documents`, `requirement_fulfillments`, `notes_summary`, `source`, `integrity` | Retire as **SoT**; not as silent live person store |
| RFE today | `validate_ready_for_employment_package_v1` | Accept orchestrator reads **explicit package** or `lead.normalized.ready_for_employment_prep_v1` — **not** snapshot table | Wire emit on Transfer; stop depending on lead prep alone |
| Persist column | `candidate_handoff_snapshots.payload` JSONB | Physically can hold RFE | **Cannot** store RFE-only without compat — see consumers |

### Snapshot consumers (break if RFE-only)

| Consumer | Fields assumed | Risk |
|----------|----------------|------|
| `hr_inbox` display name / `transfer_summary` | legacy `candidate.*` (often flat; writer is nested — already weak) | High for chips/name |
| `hr_handoff_profile_context` / `hr_document_verification` | `candidate.name/contacts`, `documents[]`, `application` | **Critical** — verification profile column |
| `hr_documents_queue` / hub summary | `candidate.name`, `documents` / `expected_documents` | Medium |
| GET `/handoffs/{id}/snapshot` | opaque JSON | API OK; callers may assume legacy |
| Employment accept/formalize | **does not** read this table | Independent |
| FE `fetchHandoffSnapshot` | unused on detail page | N/A |
| Tests / e2e fulfillments | legacy keys | High for CI |

### A conclusion → **superseded by RSO-2A CLOSED**

Chosen: **read-time compat shim** (not dual-write, not consumer-first). See **RSO-2A** section above.

---

## C — Employment init (filled)

### Architecture split (mandatory)

```text
Transfer emits manifest + pending CandidateHandoff
  → Employment policy decides (evaluate / apply)
  → Employment initializer performs Employment-owned side effects (accept_handoff path)
```

**Not:** `create_handoff` internally calls legacy Accept / mint / checklist.

Evidence: `apply_employment_accept_policy` calls `accept_handoff` only on `auto_accept`; comments forbid Recruitment Transfer from owning accept. Ritual `POST /handoffs/{id}/accept` is the **same** initializer without the ESO-1 `employment_started` audit stamp.

### Side effects by trigger

| Side effect | Trigger today | Owner | Survive removing Accept **button**? |
|-------------|---------------|-------|-------------------------------------|
| Pending `CandidateHandoff` + snapshot/manifest + `handoff_requested` + pending activity | **create** | Recruitment / handoff | N/A (create) |
| Application → `ready_for_handoff` | **create** | Recruitment | N/A |
| Handoff → `accepted` + stamps | **accept** (button **or** policy apply) | Employment | **YES** |
| Candidate → `processing_by_hr` | **accept** | Employment | **YES** |
| Application → `handed_off` | **accept** | Employment closes agency intent | **YES** |
| Audit `handoff_accepted` (+ `employment_started` on **policy apply only**) | **accept** | Employment | **YES** |
| Delayed OFF: Employee mint, HR case, doc links→employee, checklist activities | **accept** | Employment | **YES** |
| Delayed ON: HR review + doc links→`workforce_hr_review` (no Employee) | **accept** | Employment | **YES** |
| Delayed mint on approve | **approve** (separate) | Employment | Separate from Accept button |
| Formalize mint | **formalize** | Employment | Separate spine |
| Ritual pickup UI / `awaiting_hr_pickup` CTA | **button** | Frontend only | **NO** (drop when auto-accept) |

### C conclusion

Removing the Accept **button** must keep the Employment **initializer**. Auto path = Employment `apply_employment_accept_policy` after Transfer (orchestrated as Employment-owned step), not Recruitment create inlining Accept. Preserve delayed-workforce behavior as Employment policy, not Transfer.

---

## D — Read model / UI `/app/hr/handoffs/:id` (filled)

Page APIs: `GET /hr/handoffs/:id` (inbox + embedded snapshot) · `GET /handoffs/:id/hr-review` (accepted) · plus panel-specific calls.

| UI block | Primary source today | Target (Accepted boundary) | Drop snapshot as operational SoT? |
|----------|----------------------|----------------------------|-----------------------------------|
| Header / pickup **name** | Inbox `candidate_display_name` ← snapshot | **live Person** | Yes (after live name wired) |
| Pickup hero + Accept CTA | Local copy + inbox queue | Drop CTA when policy auto-accepts | CTA yes |
| Accepted hero | hr-review / employee / live Candidate | live Person + stages | Mostly yes |
| Document verification files | **Document Hub** | Hub | Already live |
| Verification **profile** column | Hybrid: Hub meta ⊕ `employee.candidate_snapshot` ⊕ handoff snapshot ns ⊕ live Candidate | **live Person** + Hub; manifest as-of only | Partial → cutover |
| Verified fields seed | `employee.candidate_snapshot` | Seed from live / authoritative facts; not copy chain | Partial |
| Start allowed | ESA + Hub evidence + employee meta | unchanged (live) | Yes (already) |
| Work eligibility | journey / workforce bundle | live | Yes |
| Contract preview | trusted identity / verified fields | live | Yes |
| **Handoff context / Why Ready** | Snapshot keys (weak vacancy shape) | **manifest** fits/verdicts + live employer/vacancy refs | Replace snapshot narrative with manifest |
| Vacancy requirements classification | **live** Candidate.vacancy_id → Vacancy | live | Already |
| `transfer_summary` chips | Derived; **unused** on detail page | optional as-of | N/A |

### D conclusion

Operational identity/docs/eligibility already lean live. Remaining snapshot dependency is naming, “Recruitment handoff” summary, and verification profile baseline — exactly the copy-chain to retire in RSO-2D after manifest + live reads.

---

## Suggested internal ladder (revised after RSO-2A)

| # | Slice | Outcome | Depends |
|---|-------|---------|---------|
| **RSO-2A** | Persist/read compatibility + Vacancy/Employer pre-mint proof | **Docs CLOSED**; feat = RFE-only persist + deprecated read-shim + access proof | Inventory |
| **RSO-2B** | Emit validated `ready_for_employment.v1` on Transfer | **PASS** — [`recruitment-employment-handoff-rso2b-emit.md`](recruitment-employment-handoff-rso2b-emit.md); gate `rso2-emit-manifest-gate` **10 passed** | 2A |
| **RSO-2C** | Employment auto-init (`apply_employment_accept_policy`); drop ritual Accept as default | **PASS** — [`recruitment-employment-handoff-rso2c-auto-init.md`](recruitment-employment-handoff-rso2c-auto-init.md) @ `5c9da75c`; gate `rso2-auto-init-gate` **7 passed**; Accept **not** inlined in `create_handoff` | 2B |
| **RSO-2D** | Consumer / read-model cutover: live + manifest decisions; lock 6 | **PASS** — [`recruitment-employment-handoff-rso2d-read-model.md`](recruitment-employment-handoff-rso2d-read-model.md) @ `aa0461d2`; gate `rso2-read-model-gate` **9 passed** | 2C |
| **RSO-2E** | **Delete compat shim** + named cutover gate | **PASS** — [`recruitment-employment-handoff-rso2e-shim-delete.md`](recruitment-employment-handoff-rso2e-shim-delete.md) @ `909ce8a5`; gate `rso2-cutover-gate` **10 passed** | 2D |

**False close:** RSO-2 “PASS” while compat shim remains the permanent HR read path.

---

## Out of scope (at RSO-2 open; later slices may land separately)

- ~~Slice 4 (`start_allowed` on Confirm)~~ → **PASS** [`employment-start-allowed-eso5-enforcement.md`](employment-start-allowed-eso5-enforcement.md)  
- Full Spine  
- New ACL product (B: no gap for Person/Documents pre-mint read)  
- Mapping Authority / Forms Publish  
- Expanding Recruitment to collect Employment lifecycle facts “just in case”  
- Dual-write legacy + RFE  
- Permanent read-shim  

---

## Next

1. **RSO-2E PASS** @ `909ce8a5` — Recruitment → Employment **boundary cutover closed**.  
2. **Boundary E2E proof PASS** — [`recruitment-employment-handoff-boundary-e2e-proof.md`](recruitment-employment-handoff-boundary-e2e-proof.md) (handoff `e9ef16f2-1ab6-49d0-91dd-aa7676995081`; one person; not Hiring E2E).  
3. **Slice 4 PASS** — [`employment-start-allowed-eso5-enforcement.md`](employment-start-allowed-eso5-enforcement.md) @ `b8c9dd04` (Confirm requires `start_allowed=true`; mint-on-confirm retired).  
4. **STOP.** Three-host Full Spine Gate = **separate decision** (not auto-opened).
