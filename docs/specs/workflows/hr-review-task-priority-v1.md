# HR review — operational task priority v1

**Status:** Accepted (default system priority).  
**Implementation:** `backend/app/services/hr_review_current_task.py` (`TASK_PRIORITY_V1`, `build_current_task`).  
**UI:** `HrCurrentTaskPanel` + BFF `task_priority_v1`, `next_action`.

---

## Nature of this document

| Property | Meaning |
|----------|---------|
| Default system priority | BFF selects one `current_task` |
| Tenant-overridable later | Future per-tenant reorder |
| Visible in UI | Step N/8 + ladder on case workspace |
| Test basis | `test_hr_review_current_task.py` |

---

## Canonical order (v1)

| Step | `task_type` | When it wins |
|------|-------------|--------------|
| 1 | `take_into_review` | Handoff `pending_review` |
| 2 | `verify_documents` | Missing docs, unverified docs, **data verification incomplete**, or `identity_verified` / `documents_uploaded` open |
| 3 | `fill_missing_data` | Journey / profile `needs_data` |
| 4 | `verify_work_eligibility` | Legal stay / permit / red paper checklist |
| 5 | `confirm_payments` | Mandatory fees |
| 6 | `prepare_zus` | ZUS readiness |
| 7 | `complete_employment_data` | Employment row incomplete |
| 8 | `ready_to_approve` | `can_approve` |

**Rule:** Top → bottom; one `current_task`.

### Step 2 (PR10+ copy)

- **Title:** “Verify candidate data and documents”  
- **Primary action:** “Start data verification” → anchor **`#hr-data-verification`**  
- **Why:** Values feed contract, ZUS, permit applications — only confirmed data becomes trusted.

Inputs: `data_verification_summary` (pending/missing/critical counts), `documents_for_approval`, checklist `identity_verified` / `documents_uploaded`.

---

## PR status

| PR | Topic | Status |
|----|-------|--------|
| PR2 | Current task BFF + panel | ✓ |
| PR3 | Document verification cards | ✓ |
| PR4 | Verified fields SoT | ✓ |
| PR5–PR8 | Identity projection, adapter, downstream, merge vars | ✓ |
| PR9 | Contract draft preview API | ✓ |
| PR10 | Unified data verification workspace | ✓ |
| PR11 | Handoff snapshot + driver docs | ✓ |

---

## PR 3 — Document verification cards ✓

Open → review fields on card → save reviewed → verify document → checklist sync (`hr_document_verification.sync_checklist_from_verifications`).

Sign-off UI: collapsed under Data Verification workspace (PR10), not a third top-level list.

---

## Later

- Tenant-specific task priority overrides  
- Contract preview UI (frontend; PR9 backend done)  
- Finalization workflow (send / sign / ePUAP)
