# RSO-2 boundary E2E proof — one test person

**Status:** **PASS**  
**Phase class:** product  
**Opened:** 2026-09-14  
**Closed:** 2026-09-14  
**Witness handoff id:** `e9ef16f2-1ab6-49d0-91dd-aa7676995081`  
**Parent:** [`recruitment-employment-handoff-rso2-cutover.md`](recruitment-employment-handoff-rso2-cutover.md) (**PASS** @ `909ce8a5`)  
**Depends on:**  
- RSO-2B emit · RSO-2C auto-init · RSO-2D read-model · RSO-2E shim delete  
- Boundary ownership **Accepted:** [`../architecture/recruitment-employment-boundary-ownership.md`](../architecture/recruitment-employment-boundary-ownership.md)  
**Does not open:** Slice 4 · ESO-5 `start_allowed` enforcement · physical Started · Full Spine · [Hiring workflow E2E](hiring-workflow-e2e.md)  

> **Proof only.** Walk **one** test person through the new Recruitment → Employment boundary.  
> Confirm the host is live authorities + immutable `ready_for_employment.v1`, not copies and not ritual Accept.  
> This is **not** the queued Hiring E2E program. After PASS, Slice 4 is still a **separate decision**.

---

## Original Goal → Completion Proof

**Problem this slice must permanently remove:**  
Cutover gates are green, but nobody has walked **one** person through Transfer → auto-init → `/app/hr/handoffs/:id` to see that HR actually gets the right live person, live docs, live target work, and frozen Why Ready — before locking Confirm behind `start_allowed`.

**Completion proof (named consumer):**

```text
One test candidate (internal_hr)
  → operator Transfer
  → CandidateHandoffSnapshot.payload = ready_for_employment.v1 only
  → Employment auto-init (no Take into HR review)
  → GET/UI /app/hr/handoffs/:id
       live Person (name / contacts / citizenship)
       live Documents / Hub (no file copies)
       live employer / vacancy
       Why Ready = frozen fits / verdicts / evidence refs / as-of
  → no re-entry of Recruitment-known facts as a required chore
  → Slice 4 / Started untouched
```

**False close (reject):** green unit gates without a person walk; seeding a fake HR dossier; reconstructing Why Ready in the browser from snapshot; claiming Hiring E2E program PASS; opening Slice 4; Confirm/`start_allowed`/physical Started.

---

## Named consumer path (locked)

```text
Transfer
  → emit ready_for_employment.v1
  → Employment auto-init
  → /app/hr/handoffs/:id
       live Person
       + live Documents / Hub
       + live target work
       + Why Ready (manifest)
```

One person. One handoff. `destination=internal_hr`.

---

## Scope (in)

1. Prepare **one** test candidate already Ready for Transfer (existing authorities; no new Recruitment collection).  
2. Execute Transfer and record: payload `contract_id`, auto-init outcome, handoff status.  
3. Open HR host `/app/hr/handoffs/:id` (inbox row API is the same contract).  
4. Witness: identity/contacts/citizenship current = live Person; vacancy/employer current = live entities; documents/files/status = Hub; Why Ready = backend `why_ready` from manifest.  
5. Witness: no ritual Accept as the happy path; no mandatory re-key of facts already known at Transfer.  
6. Record PASS evidence (handoff id, payload discriminator, screenshots or API dumps of `why_ready` / `live_target_work` / display name).

---

## Scope (out)

| Out | Owner |
|-----|--------|
| Slice 4 / Confirm requires `start_allowed` | **Closed** |
| Physical Started / ESO-5 semantics | **Closed** |
| Hiring workflow E2E program / RS-7 | **Not this brief** |
| Full Spine | **Closed** |
| New ACL, emit/init rewrite, Formalize | **Forbidden** |
| Many candidates / load / CI product suite | **Out** |

---

## PASS criteria (witness)

- [x] Snapshot payload for this handoff is **RFE-only** (`contract_id = ready_for_employment.v1`; no legacy snapshot writer for `internal_hr`)  
- [x] Auto-init ran; handoff is **accepted** (or policy blockers shown) **without** ritual Accept as the operator step  
- [x] HR header/inbox name is the **same live Person** as Recruitment  
- [x] Employer / vacancy labels match **live entities** for that person’s target work  
- [x] Documents on the case are **Hub objects** (same ids as Recruitment), not copies  
- [x] Why Ready fits / verdicts / evidence refs / as-of match the **frozen Transfer manifest**  
- [x] Current values are **not** taken from manifest identity as SoT  
- [x] No required re-entry of Recruitment-known identity/contacts/docs  
- [x] Slice 4 / `start_allowed` enforcement / physical Started **not touched**  

---

## Witness notes (2026-09-14)

| Field | Value |
|-------|--------|
| Candidate id | `c0832430-a22d-42a3-893e-c54fe12f44a8` |
| Handoff id | `e9ef16f2-1ab6-49d0-91dd-aa7676995081` |
| Destination | `internal_hr` |
| `contract_id` | `ready_for_employment.v1` |
| Snapshot keys (RFE-only) | `contract_id`, `tenant_id`, `person`, `target_work`, `recruitment_facts`, `evidence`, `fits_decision`, `context_refs` |
| Auto-init | `status=accepted`, `accepted_at=2026-09-14T13:27:24.325265Z` on Transfer response; **no** `POST /handoffs/{id}/accept` |
| Workforce | `workforce_employee_id=fa81d0b6-f63a-4054-9032-abfa9664fefb` |
| Live name | `Boundary E2Ea61a6a17` (Recruitment + `GET /hr/handoffs/{id}` `candidate_display_name`) |
| Live contacts | `+48500111222` / `boundary.e2e.a61a6a17@example.com` |
| Live citizenship | `UA` |
| Live employer / vacancy | `Test Logistics Sp. z o.o.` / `Vacancy conversion idemp` (`live_target_work.employer_name` from live company; manifest `target_work` has ids + `vacancy_title_as_of` only) |
| Hub document ids | **Same 11 ids** before and after Transfer (no copies) |
| Why Ready | Backend `why_ready.contract_id=ready_for_employment.v1`; `fits_decision` identical to manifest; includes `requirement_verdicts_as_of`, `evidence_refs`, `as_of`, `target_work_as_of` |
| Ritual Accept | Absent on happy path |
| Slice 4 | **Not opened** |

**Ops / deploy-proof note (keep):** First Transfer against a long-lived docker backend (uvicorn **without** `--reload`, process up for days) still wrote a **legacy** snapshot. That was **not** a defect of the new boundary semantics — the worker was still running **pre-cutover imported code**. After `docker compose restart backend`, the same Ready-for-Transfer candidate emitted RFE-only + auto-init. Witness above is the post-restart Transfer. Future production/deploy proofs must restart or otherwise ensure the running process loads the cutover revision before treating Transfer payload shape as evidence.

**Host API used:** `GET /api/v1/hr/handoffs/{id}` (route surface for `/app/hr/handoffs/:id`).

---

## After PASS

1. Stamp this brief with witness notes (handoff id + date). ✅  
2. **STOP.** Do not open Slice 4 in the same change.  
3. Separate decision: whether ESO-5 Confirm may now require `start_allowed`.

---

## Implementation map (inspect, do not retouch)

| Concern | Location |
|---------|----------|
| Emit | `ready_for_employment_emit.py` / `handoff_snapshot.py` |
| Auto-init | `apply_employment_accept_after_transfer` |
| Host read model | `hr_handoff_read_model.py` · `hr_inbox.py` |
| Why Ready UI | `HrHandoffContextSummary.tsx` (display only) |
| Host route | `/app/hr/handoffs/:id` |
