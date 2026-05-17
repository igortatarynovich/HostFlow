# HR Acceptance Workflow — state machine (Stage A → B)

**Purpose:** canonical states and transitions before Stage B splits `accept_handoff` from `approve_for_employment`.  
**Stage A (shipped):** `workforce_hr_reviews` + review UI; **`accept_handoff` unchanged** — workforce row still created on accept.  
**Stage B (planned):** accept = “take into processing”; approve = “accepted for employment” + downstream payroll/ZUS/automation gates.

**Related:** commit `73f101e` (Stage A slice), [implementation-roadmap-single-tenant-hr-handoff.md](implementation-roadmap-single-tenant-hr-handoff.md), [handoff-contract.md](../architecture/handoff-contract.md).

---

## 1. Roles (who moves what)

| Actor | Action | Meaning (target) |
|-------|--------|------------------|
| Recruitment | Handoff / stage → ready | Candidate transferred to HR queue |
| HR | **Accept** (Stage B) | HR took ownership; employee shell may exist but **not** employment-approved |
| HR | Review checklist / corrections | Operational readiness |
| HR | **Approve** (Stage B) | Accepted **for employment** — unlock payroll/ZUS branch, full active employee, automations |
| HR | Return / Reject | Exit paths back to recruitment or terminal HR decision |

---

## 2. Canonical states (cross-entity)

States below are **logical** names for orchestration. Stage A implements the **review** subset on `workforce_hr_reviews.status`; handoff/employee states catch up in Stage B.

### 2.1 Happy path

```
handoff_pending
    → accepted_by_hr          # HR accept (Stage B: no longer implies employment approval)
    → hr_review_in_progress   # checklist sync + HR work started
    → hr_approved             # approve_for_employment (Stage B)
    → employment_pending      # contract/ZUS/payroll branch in flight
    → employed                # active employment confirmed
```

### 2.2 Waiting / correction substates (review layer)

While in `hr_review_in_progress`, derive **display/wait** status from blockers (Stage A already maps these on `workforce_hr_reviews`):

- `waiting_documents` — includes explicit corrections note
- `waiting_payments`
- `waiting_work_permit`
- `waiting_red_paper`

Alias product language: **`needs_more_documents`** ≈ `waiting_documents` + corrections requested.

### 2.3 Terminal / exit states

| State | Entity | Notes |
|-------|--------|-------|
| `returned_to_recruitment` | review (+ handoff return) | Stage A: `return_hr_review_to_recruitment` |
| `rejected_by_hr` | review | Stage A: `reject_hr_review` |
| `hr_rejected` | alias | Same as `rejected_by_hr` in API/UI copy |

---

## 3. Stage A mapping (today)

| Logical | `CandidateHandoff` / inbox | `WorkforceEmployee` | `workforce_hr_reviews.status` |
|---------|---------------------------|---------------------|-------------------------------|
| handoff_pending | pending / inbox | may not exist | — |
| accepted_by_hr | accepted | **created on accept** (unchanged) | `hr_review_in_progress` (ensure on accept) |
| hr_review_in_progress | accepted | exists | `hr_review_in_progress` or waiting_* |
| hr_approved | accepted | exists | `approved_for_employment` |
| returned_to_recruitment | returned | exists or frozen | `returned_to_recruitment` |
| hr_rejected | — | exists | `rejected_by_hr` |

**Invariant (Stage A):** `approve_hr_review` does **not** move handoff accept semantics or delete workforce; it only sets review status and audit fields.

---

## 4. Stage B target transitions (to implement once)

### 4.1 Commands → effects

| Command | From (min) | To | Side effects (allowed) |
|---------|------------|-----|------------------------|
| `accept_handoff` | `handoff_pending` | `accepted_by_hr` | Create/link employee **shell**, HR case, inbox; **no** employment-approved flag |
| `start_hr_review` | `accepted_by_hr` | `hr_review_in_progress` | `ensure_hr_review_for_employee` (idempotent) |
| `sync_hr_review` | `hr_review_in_progress` | same or waiting_* | Recompute checklist/blockers only |
| `approve_for_employment` | `hr_review_in_progress` (no required blockers) | `hr_approved` → `employment_pending` | Set employment-approved; enqueue payroll/ZUS/onboarding automations |
| `return_to_recruitment` | review active | `returned_to_recruitment` | Handoff return path (existing) |
| `reject_by_hr` | review active | `rejected_by_hr` | Terminal review; workforce policy TBD |
| `confirm_employment` | `employment_pending` | `employed` | Employment row active; employee status `active` |

### 4.2 Forbidden (enforce in service layer, not scattered `if`)

- `approve_for_employment` when required checklist has blockers → `422 HR_REVIEW_BLOCKED` (Stage A behaviour).
- `approve_for_employment` from `handoff_pending` without `accepted_by_hr`.
- Workforce creation **only** on approve (Stage B breaking change — feature-flag per tenant during migration).
- Auto-transition `accept` → `approved` (explicitly out of scope).

---

## 5. Implementation notes for Stage B

1. **Single orchestrator** module (e.g. `hr_acceptance_orchestrator.py`) owns transitions; routers call commands only.
2. **Persist logical state** on handoff + review (+ optional `employment_approval_at` on employee) — avoid inferring only from checklist JSON.
3. **Events** (activity log): one event per transition; consumers subscribe — no duplicate side effects in accept and approve.
4. **Migration:** tenants with existing employees mid-review stay on Stage A mapping until backfill sets `accepted_by_hr` + review row.

---

## 6. Checklist before Stage B PR

- [ ] ADR or section in handoff-contract updated for accept vs approve
- [ ] Feature flag: `hr_accept_v2` or tenant setting for delayed workforce creation
- [ ] Integration tests: accept without approve → no payroll automation; approve → automations fire once
- [ ] UI: rename CTAs (“Take into processing” vs “Approve for employment”)
- [ ] Remove Stage A assumption in docs §3 table (workforce on accept)
