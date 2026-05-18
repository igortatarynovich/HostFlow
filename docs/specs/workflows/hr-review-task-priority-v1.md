# HR review — operational task priority v1

**Status:** Accepted (default system priority).  
**Implementation:** `backend/app/services/hr_review_current_task.py` (`TASK_PRIORITY_V1`, `build_current_task`).  
**UI:** `HrCurrentTaskPanel` + BFF field `task_priority_v1`.

---

## Nature of this document

This order is **not** eternal business truth. It is the **first product canon**:

| Property | Meaning |
|----------|---------|
| Default system priority | Used by BFF when selecting `current_task` |
| Tenant-overridable later | Future: per-tenant reorder or disable steps |
| Visible in UI | Step N/8 + collapsible v1 ladder on case workspace |
| Test basis | Unit tests assert first-match rule and ordering |

---

## Canonical order (v1)

| Step | `task_type` | When it wins |
|------|-------------|--------------|
| 1 | `take_into_review` | Handoff not accepted into HR work (`pending_review`) |
| 2 | `verify_documents` | Missing or unverified required hire documents |
| 3 | `fill_missing_data` | Identity / citizenship / work country / journey `needs_data` |
| 4 | `verify_work_eligibility` | Legal stay, work permit, red paper not confirmed |
| 5 | `confirm_payments` | Mandatory fees block submission |
| 6 | `prepare_zus` | ZUS readiness not closed while review is otherwise advanced |
| 7 | `complete_employment_data` | Contract / employment row incomplete |
| 8 | `ready_to_approve` | No blockers; `can_approve` |

**Rule:** Evaluate top → bottom; emit **one** `current_task`. Do not merge competing tasks in v1.

---

## PR 2 outcomes (done)

- One dominant `current_task` on HR review panel (BFF-owned, not frontend guesswork).
- `HrCurrentTaskPanel` is primary; right rail is secondary orchestration.
- HR sees why the task was chosen, what it blocks, primary action, and what happens after.

---

## PR 3 — Document verification cards ✓

**Goal:** Replace “checkbox for checkbox’s sake” with a verification **action**:

1. Open document (resolver `open_url`).
2. Review fields on card (extracted / displayed metadata).
3. Confirm data against checklist expectations.
4. Link satisfaction to checklist item (`documents_uploaded`, per-doc keys).
5. Only then mark document **verified** in approval list.

**Out of scope for PR 3:** verified-fields SoT (PR 4), OCR pipeline, new workflow engine, document mutation beyond existing HR APIs.

---

## PR 4+ (later)

- Verified fields model — SoT for contract / ZUS / payroll.
- Tenant-specific task priority overrides.
