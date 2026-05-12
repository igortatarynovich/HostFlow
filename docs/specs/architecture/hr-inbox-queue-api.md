# HR Inbox / Queue API (v1)

Spec-first contract for the **internal-HR lane** work queue. No UI in this phase: HTTP API only.

## Purpose

Give HR operators a **single queue surface** that is grounded in:

- what recruitment **officially transferred** (immutable snapshot at `create_handoff`);
- **current workflow state** (handoff status, activities, workforce);
- **live operational context** (documents today, candidate row today) only where needed — **not** as the source of truth for “what was transferred”.

This avoids collapsing recruitment and HR back into one “live candidate” view for accountability and disputes.

## Core rule

**HR Inbox must not be built primarily from `Candidate`.**

Correct composition:

| Concern | Primary sources |
|--------|-------------------|
| Fact of transfer (“what we handed over”) | `candidate_handoffs` + `candidate_handoff_snapshots.payload` |
| Transfer lifecycle | `candidate_handoffs` (`status`, `requested_at`, `accepted_at`, …) |
| What to do now | `activities` (HR types, assignees, due dates) |
| HR employee record | `workforce_employees` (post-accept materialization) |
| Historical document set at transfer | `snapshot.documents` inside payload |
| Current document reality | live `documents` (tenant-scoped; operational) |

`Candidate` may appear only as **secondary / live** context (e.g. current stage, operational patches allowed under HR lane policy), never as the canonical “transfer package”.

## Data sources (normative)

| Block | Source | Notes |
|-------|--------|--------|
| What was transferred | `candidate_handoff_snapshots.payload` | Immutable v1 JSON; written on `create_handoff`, not on accept. |
| Handoff status | `candidate_handoffs` | e.g. `pending_review`, `accepted`, …; `destination = internal_hr` for this API. |
| What to do now | `activities` | Pending accept task (`internal_hr_handoff_pending`), post-accept checklist (`handoff_hr_checklist`), etc. |
| HR / workforce row | `workforce_employees` | Linked after accept; `meta.internal_hr_handoff_id` ties back to handoff. |
| Current documents | live `documents` | For operational queues (missing / expiring) — **not** implemented in the first backend PR; contract below. |
| Historical documents at transfer | snapshot `documents` | For audit / “what recruitment asserted”. |

## Endpoints (v1)

Base path: `/api/v1/hr` (full URLs: `/api/v1/hr/handoffs/pending`, etc.).

All routes require:

- authenticated user;
- tenant workspace (`X-Tenant-Id` / `get_db_with_tenant`);
- **HR module enabled** (same gate as workforce HR: `tenant.settings.modules.hr`);
- role in **`hr_officer` | `administrator` | `supervisor`** (aligned with HR workspace access patterns).

| Method & path | Purpose |
|---------------|---------|
| `GET /handoffs/pending` | Internal-HR handoffs awaiting accept (`pending_review`, `destination = internal_hr`). |
| `GET /handoffs/accepted` | Internal-HR handoffs already accepted (in HR ownership / workforce pipeline). |
| `GET /tasks` | HR operational activities (checklist + pending-accept reminders), filtered to HR handoff-related types. |
| `GET /documents/missing` | **Contract only (v1):** documents required for HR/onboarding that are absent or invalid — **not implemented** in the first PR; implement against live `documents` + policy, not snapshot alone. |
| `GET /documents/expiring` | **Contract only (v1):** documents approaching expiry — **not implemented** in the first PR; same separation: live documents + SLA rules. |

### Query parameters (v1)

**Handoff lists** (`pending`, `accepted`):

- `limit` (default `50`, max `200`)
- `offset` (default `0`)

**Tasks** (`tasks`):

- `assignee_scope`: `mine` | `team` (default `mine`). `team` returns tenant-wide rows for the HR task types (intended for leads); restricted to roles that already use team scope elsewhere (`administrator`, `supervisor`, `hr_officer`, `superadmin`).
- `limit` (default `100`, max `500`)

## Response shape (v1)

### `GET …/handoffs/pending` and `…/accepted`

JSON object:

- `total` — total matching rows (before pagination).
- `items` — array of:
  - `handoff` — same fields as public handoff DTO (`HandoffOut`-compatible): ids, status, timestamps, `destination`, `candidate_id`, client routing fields, etc.
  - `snapshot` — full `candidate_handoff_snapshots.payload` object, or `null` if no row (legacy handoffs pre-snapshot).
  - `workforce_employee_id` — present when a `workforce_employees` row exists for this handoff (`meta.internal_hr_handoff_id`); otherwise `null`. Typically populated after accept.

No requirement to embed full live `Candidate` in v1.

### `GET …/tasks`

JSON object:

- `items` — list of activity/reminder rows (`ReminderOut`-compatible), same enrichment rules as `GET /api/v1/activities` (titles, merges, etc.).

Filtered `type` values (v1):

- `internal_hr_handoff_pending`
- `handoff_hr_checklist`

## Implementation notes

- **Ordering:** pending handoffs by `requested_at` descending (newest first); accepted similarly (can refine by `reviewed_at` / `accepted_at` later).
- **Soft-deleted candidates:** excluded from handoff lists (join `candidates.deleted_at IS NULL`).
- **Recruitment roles** (`recruiter`, …) must **not** call this router for production UX; they continue to use recruitment APIs. Enforced by role dependency.

## Evolution

- **Acceptance metadata** on snapshot (second write): `accepted_at`, `accepted_by`, `acceptance_context` — optional future revision; inbox continues to read live `candidate_handoffs` for status.
- **Missing / expiring** endpoints: separate PR; must consume live `documents` + gates, optionally cross-check against snapshot for drift diagnostics (not as sole source).
