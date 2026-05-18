# HR Employment Case Workspace

**Status:** Accepted (UX architecture, PR 1 shell).  
**Related:** [ADR-014 document hub access](../architecture/ADR-014-document-hub-access-model.md), [HR handoff separation](current-separation-status-recruitment-hr-doc-hub.md).

---

## Problem

Before `approve_for_employment`, HR does **not** work on an “employee profile”. They work on an **employment case**: verify documents, confirm eligibility, decide hire.

Showing payroll, ZUS, absences, onboarding, and full compliance dumps on the same screen as HR review creates cognitive noise and implies a false “source of truth” (documents in three places, checklist detached from data).

---

## Concepts

| Concept | Meaning |
|--------|---------|
| **Employment Case** | UI + process mode while HR review is open and hire is not approved. Candidate-linked workforce row may exist; product surface is **case**, not employee lifecycle. |
| **Employee Operational Profile** | UI mode after `approved_for_employment`. Onboarding, payroll, ZUS, absences, contracts, full journey. |
| **Document Hub** | Storage and file access (`document_id`, `open_url`). Not the HR decision workspace. |
| **Employment Case (process)** | Checklist, documents for approval, eligibility summary, approve / return / reject. |

**Rule:** Document Hub answers “where is the file?”. Employment Case answers “can we hire?”.

---

## Mode switch (frontend)

BFF field on HR review panel: `mode`

| `mode` | When | Page title / nav |
|--------|------|------------------|
| `hr_review_case` | `status !== approved_for_employment` | “HR review case”; back link → HR Inbox |
| `employee_profile` | `status === approved_for_employment` | “Employee profile”; back link → HR · Employees |

Handoff detail route (`/app/hr/inbox/:handoffId`) is **always** case-style (never employee operational sections).

---

## PR 1 — visible layout (review case)

**Main column only:**

1. Hero (stage, blockers, current message)
2. HR review panel (checklist, decision actions)
3. Documents required for approval (single doc list for review)
4. Compact work eligibility summary
5. Short recruitment handoff summary (read-only)

**Right rail only:**

- Next action, blockers, readiness, timeline (orchestration — no payroll/forms)

**Hidden until approve:**

- Payroll, tax, insurance, ZUS legal layer, compliance state dump, contracts, onboarding list, absences, leave, full work eligibility journey, full linked-documents table (duplicate of approval list), overview hire fields where redundant.

---

## Follow-up PRs (out of scope for PR 1)

| PR | Deliverable |
|----|-------------|
| PR 2 | Current task engine — one dominant main task |
| PR 3 | Document verification cards (preview + extracted fields) |
| PR 4 | Verified fields model — SoT for contract / ZUS / payroll |

---

## Acceptance (PR 1)

HR opens a case before approve and:

- Sees stage, next action, and approval blockers without payroll/ZUS/absences noise.
- Uses one primary document list (`documents_for_approval`), not three competing surfaces.
- Does not see long accordion dump of post-hire modules.
- After approve, the same employee URL shows operational profile sections.
