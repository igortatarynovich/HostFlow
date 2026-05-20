# HR Employment Case Workspace

**Status:** Accepted (PR1–PR11 implemented on branch `feat/f8-52-legal-documents-controls`).  
**Related:** [Data Verification Workspace](hr-data-verification-workspace.md), [ADR-014 document hub access](../architecture/ADR-014-document-hub-access-model.md), [HR handoff separation](current-separation-status-recruitment-hr-doc-hub.md), [Task priority v1](hr-review-task-priority-v1.md), [Verified fields](hr-verified-fields-model.md), [Employment identity](hr-employment-identity-projection.md), [Trusted read adapter](hr-employment-identity-read-adapter.md), [Contract draft preview](hr-contract-generation-mvp.md).

---

## Problem

Before `approve_for_employment`, HR does **not** work on an “employee profile”. They work on an **employment case**: verify recruiter data against documents, confirm eligibility, decide hire.

Showing payroll, ZUS, absences, onboarding, and full compliance dumps on the same screen as HR review creates cognitive noise and implies a false “source of truth” (documents and blockers in many places).

---

## Concepts

| Concept | Meaning |
|--------|---------|
| **Employment Case** | UI + process mode while HR review is open and hire is not approved. |
| **Employee Operational Profile** | UI mode after `approved_for_employment`. Onboarding, payroll, ZUS, absences, contracts. |
| **Document Hub** | Storage and file access (`document_id`, `open_url`). Not the HR decision workspace. |
| **Data Verification** | Primary case work: confirm recruiter values per field, linked to source document. |

**Rule:** Document Hub answers “where is the file?”. Employment Case answers “can we hire?”.

---

## Mode switch (frontend)

BFF field on HR review panel: `mode`

| `mode` | When | Page title / nav |
|--------|------|------------------|
| `hr_review_case` | `status !== approved_for_employment` | “HR review case”; back → HR Inbox |
| `employee_profile` | `status === approved_for_employment` | “Employee profile”; back → HR · Employees |

Handoff detail route (`/app/hr/inbox/:handoffId`) is **always** case-style.

---

## Implementation map (PR1–PR11)

| PR | Deliverable | Spec |
|----|-------------|------|
| PR1 | Case shell, mode gating, hero, rail, hide post-hire modules | this doc |
| PR2 | `current_task` + `task_priority_v1` + `HrCurrentTaskPanel` | [task priority v1](hr-review-task-priority-v1.md) |
| PR3 | Document verification cards, checklist sync from doc state | [task priority v1 § PR3](hr-review-task-priority-v1.md#pr-3--document-verification-cards-) |
| PR4 | `workforce_hr_verified_fields` SoT | [verified fields](hr-verified-fields-model.md) |
| PR5 | `employment_identity` projection on panel | [identity projection](hr-employment-identity-projection.md) |
| PR6 | Trusted read adapter + consumer matrix | [read adapter](hr-employment-identity-read-adapter.md) |
| PR7 | Wire merge / ZUS task / payroll prep to adapter | read adapter § PR7 |
| PR8 | `trusted_identity.*` merge vars + prep-status API | read adapter § PR8 |
| PR9 | Contract **draft preview** API + UI panel (trusted only) | [contract generation](hr-contract-generation-mvp.md) |
| PR10 | **Data Verification Workspace** (unified UI + BFF items) | [data verification](hr-data-verification-workspace.md) |
| PR11 | Handoff snapshot recruiter values + driver/Code95/tacho docs | [data verification § sources](hr-data-verification-workspace.md#recruiter-value-sources-pr11) |
| PR12 | Sequential document verification UX | [data verification § PR12](hr-data-verification-workspace.md#ui-review-case-layout-pr12) |
| PR12b | Role-based required fields (`position_category=driver`) | [data verification § policy](hr-data-verification-workspace.md#required-for-approval-policy-position) |
| — | Recursion fix: `ensure_hr_review(sync_from_sources=False)` in trusted read during journey | read adapter § Operational notes |

**Migrations (deploy order):** `202605181400_hr_doc_verify` → `202605181500_hr_verified`.

---

## Review case layout (current, PR10+)

**Main column:**

1. Hero (stage, blockers, message)  
2. **Sequential document verification** (`HrSequentialDocumentVerification`, `#hr-document-verification`)  
3. HR review panel — **case decision mode** (readiness + approve; checklist admin-only)  
4. Supporting (collapsed): contract draft preview, compact eligibility, recruitment handoff summary  

**Right rail:** next action, **one** blocker summary, readiness (checklist + data verification counts), timeline.

**Not shown as primary blocks in review mode:**

- Duplicate document lists, separate verified-fields table, full identity grid, payroll/ZUS/absences.

---

## Post-approve

Same employee URL switches to `employee_profile`: operational sections, optional data verification / contract preview when identity allows.

---

## Acceptance

HR opens a case before approve and:

- Sees **one** verification workspace with recruiter values and per-field actions.  
- Does not re-type data that came from recruitment when handoff snapshot exists.  
- Uses checklist + rail as **summary**, not competing full blocker lists.  
- After approve, operational profile replaces case layout.
