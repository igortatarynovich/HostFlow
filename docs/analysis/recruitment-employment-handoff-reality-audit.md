# Recruitment → Employment Handoff Reality Audit

**Status:** research draft (inventory / reality check — **not** redesign)  
**Date:** 2026-09-13  
**Measured against:** runtime Transfer path (`create_handoff` → snapshot → `/app/hr/handoffs/:id` → accept → `handoff_from_candidate`)  
**Contract SoT (not emitted at runtime):** [`../specs/architecture/ready-for-employment-contract.md`](../specs/architecture/ready-for-employment-contract.md) (`ready_for_employment.v1`)  
**Depends on (closed, unchanged):** Slice 1–3 `employment_start_allowed` — downstream admit-to-work; **not** invalidated by this audit  

> **This document is a factual inventory.** It does not redesign the boundary, open RSO-2, open Slice 4, or claim Full Spine.  
> Slice 3 PASS remains valid. Next product step after this audit is a **gap decision**, not automatic implementation.

---

## Sequencing (locked)

```text
Slice 3 PASS
  → STOP
  → Handoff Reality Audit (this file)
  → gap decision (known Recruitment facts vs Employment-only missing)
  → boundary fix OR Slice 4
```

**Closed until gap decision:** Full Spine · Slice 4 (ESO-5 Confirm requires `start_allowed`) · RSO-2 emit/cutover implementation.

---

## Key verdict

| Claim | Reality |
|-------|---------|
| `ready_for_employment.v1` exists as Accepted contract (RSO-1) | **Yes** — shape + validate API + gate tests |
| Runtime Transfer emits `ready_for_employment.v1` | **No** — `create_handoff` / `build_handoff_snapshot_payload_v1` never call validate/emit |
| RSO-2 (`fits` → package → `offer_handoff`) | **Absent** — happy path still legacy handoff + snapshot |
| Documents copied into HR | **No** — Hub authorities; accept links `reused_for_hr` |
| Package boundary complete for Employment reuse | **No** — pending handoff + legacy snapshot; HR reconstructs after Accept |
| Operator services the boundary (ritual Accept, re-verify, re-enter context) | **Yes** — fails contract gate 3 in spirit until cutover |

**Bottom line:** Transfer today creates a **pending `CandidateHandoff` + immutable legacy snapshot**, not a frozen canonical `ready_for_employment.v1` package. Employment (HR) starts with `candidate_id` + partial context and **reconstructs the person/context after Accept**, rather than continuing from a complete Recruitment terminal package.

---

## What Transfer actually creates

Operator action: **Передать на трудоустройство** → `create_handoff` with `destination=internal_hr`.

| Object | When | Notes |
|--------|------|--------|
| `CandidateHandoff` | create | `pending_review`; IDs: `candidate_id`, `client_company_id` / `client_tenant_id`, `from_company_id`, `to_company_id`, `application_id` |
| `CandidateHandoffSnapshot` | create | Legacy JSON v1 (`build_handoff_snapshot_payload_v1`) — **not** `ready_for_employment.v1` |
| Pending HR activity + notify | create | Inbox pickup |
| `WorkforceEmployee` | **accept only** | `accept_handoff` → `handoff_from_candidate` (+ delayed-workforce tenant flag may defer mint) |
| Document file copies | never | Forbidden; links only |

Candidate stage stays `ready_for_handoff` / `ready_for_hr` until Accept.

Evidence paths: `backend/app/services/handoff.py` (`create_handoff`, `persist_handoff_create_snapshot`), `handoff_snapshot.py`, `hr_acceptance_orchestrator.py`, `workforce_hr_operational_context.py`.

---

## Reality matrix

| Data / evidence | Recruitment authority | In handoff package (legacy snapshot / row) | HR receives | Re-enters / confirms | Gap |
|-----------------|----------------------|--------------------------------------------|-------------|----------------------|-----|
| **identity** | Candidate columns + `personal_data` / contacts | `candidate.name`, contacts, birth_date, address fields | Display name; after Accept — `employee.candidate_snapshot` + verified-field seed | Confirms vs docs in verification workspace | Continuity via snapshot copy, not identity contract |
| **citizenship** | `personal_data` / `extra` | `candidate.citizenship` | transfer_summary / profile seed if present | May re-check in verified fields / eligibility | Empty if Recruitment never stored it |
| **employer** | company / vacancy / handoff client IDs | **IDs on row only**; no employer name block in snapshot | `HandoffOut` IDs; UI summary barely surfaces employer | Reconstructs employer context in Workforce/HR | **GAP** — not a first-class package fact |
| **vacancy / position** | Application + Vacancy | Nested `application.{vacancy_id,vacancy_title,recruiter}`; no `position_category` in handoff snapshot | Nested in snapshot; UI often misses title (looks for top-level / `snapshot.vacancy`) | Position/category often from employee snapshot / eligibility after Accept | **GAP** — weak UI + incomplete position facts |
| **qualification / fits verdict** | Requirements / transfer readiness / fulfillments | `requirement_fulfillments[]`, `expected_documents[]` — **no** `fits_decision` block | Fulfillments via snapshot API; not shown as named fits verdict | Own HR verification plan | **GAP vs contract** — no `fits_decision` emit |
| **residence / work facts** | Candidate `extra` / `personal` | Mostly absent (`work_country` only in snapshot v1) | After Accept — eligibility seed from live candidate + richer employee snapshot | Formalize / eligibility / permit fields | **GAP** — not frozen on Transfer |
| **documents** | Document Hub on `candidate_id` | Snapshot: type/status/dates/canonical **without `document_id`**; ids in fulfillments | **Same Hub docs** via `reused_for_hr` (not copies) | HR-lane checks (do not clobber Recruitment status) | Link scope: approved fulfillments **or** legacy “all active docs” |
| **evidence metadata** | `candidate_evidence` → fulfillments | `requirement_fulfillments[]` | Snapshot + Hub + handoff profile namespace | Confirms fields from documents | Snapshot document list alone is thin; SoT = Hub + fulfillments |
| **planned start** | Not handoff SoT today | **Absent** | Not until Formalize / hire / start_allowed context | HR/Employment later | Do **not** auto-pull into Recruitment without ownership decision |
| **contract basis** | Not handoff SoT today | **Absent** | Formalize (`confirm_employment_contract_basis`) | HR Formalize | Do **not** auto-pull into Recruitment without ownership decision |
| **field_answers** | Lead `normalized.field_answers` | **Not in snapshot** | Only if already mapped onto Candidate | Else Lead-only / reopen Recruitment | Recruitment/Lead-local residual |

---

## What `/app/hr/handoffs/:id` shows

**Before Accept (pickup):** name, handoff status, Accept CTA, thin “Recruitment handoff” summary (name + date; vacancy often missing due to shape mismatch).

**After Accept:** Employee + HR review, document verification, work eligibility, Slice 3 Start Allowed panel (when Employee linked), read-only handoff summary, link back to recruitment record.

HR does **not** receive a validated `ready_for_employment.v1` payload. Host is pending/accepted handoff + legacy snapshot + post-Accept reconstruction.

---

## Contract vs runtime (explicit)

| `ready_for_employment.v1` block | Runtime Transfer |
|---------------------------------|------------------|
| `contract_id` | Not set |
| `tenant_id` | Implicit via handoff row / tenant session — not package field |
| `person` | Partial via `candidate` snapshot block |
| `target_work` | Partial nested application/vacancy IDs + title; employer name missing |
| `recruitment_facts` | Not a named block; scattered candidate fields + fulfillments |
| `evidence` | Partial via fulfillments + document metadata |
| `fits_decision` | **Not emitted** |
| `context_refs` | Partial (`application_id` on row / application block) |

RSO-1 contract text already states: legacy `build_handoff_snapshot_payload_v1` is **not** this contract; cutover is a later runtime slice (**RSO-2**). This audit confirms cutover has **not** happened.

---

## What this audit does **not** decide

- Which fields belong in the first production `ready_for_employment.v1` package vs Employment-only missing after Transfer.  
- Whether `planned_start` or `contract basis` are Recruitment-owned (default: **do not** auto-move them into Recruitment).  
- Whether to open RSO-2 implementation, Slice 4, or a narrower boundary fix first.

---

## Next decision (required before RSO-2 / Slice 4)

Opened: [`../specs/architecture/recruitment-employment-boundary-ownership.md`](../specs/architecture/recruitment-employment-boundary-ownership.md) (**Proposed**) — categories `REQUIRED_AT_TRANSFER` / `PASS_IF_KNOWN` / `EMPLOYMENT_OWNED`, Transfer semantics, Accept≠button, HR verification split.

```text
known Recruitment facts
  → frozen canonical package (ready_for_employment.v1)
  → Employment-only missing (HR may collect after Transfer)
```

Until that decision is **Accepted**:

- Do **not** open RSO-2 implementation.  
- Do **not** open Slice 4 or Full Spine.  
- Slice 1–3 `start_allowed` remain closed correctly as downstream mechanics.

After Accept: RSO-2 = cutover existing `CandidateHandoff` to `ready_for_employment.v1` + auto-init; Slice 4 only after that cutover.

---

## Refs (implementation context — not canon)

- `backend/app/services/handoff.py` — create / accept  
- `backend/app/services/handoff_snapshot.py` — legacy snapshot v1  
- `backend/app/reference/ready_for_employment.py` — contract machine copy (validate only)  
- `backend/app/services/hr_inbox.py` — inbox row + transfer_summary shape  
- `hostflow-frontend/src/pages/hr/HrHandoffDetailPage.tsx` — host UI  
- `docs/specs/tasks/employment-start-allowed-hr-host-binding.md` — Slice 3 PASS; next = this audit → gap decision  
- `docs/specs/tasks/recruitment-spine-orchestrator-v1.md` — RSO-2 still the runtime cutover slice (not opened here)
