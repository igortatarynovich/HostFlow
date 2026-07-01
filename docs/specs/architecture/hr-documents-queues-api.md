# HR Documents Queues API (v1)

Operational queues for **internal-HR lane**: what is still required vs what is expiring, grounded in **ruleset + live documents**, with **handoff snapshot** as historical context only.

Base path: `/api/v1/hr/documents/…` (same HR module + role gates as `hr-inbox-queue-api.md`).

## Endpoints (v1)

| Method & path | Purpose |
|---------------|---------|
| `GET /missing` | Required-by-matrix types that lack a **live valid** document row. |
| `GET /expiring` | **Live** documents with `expires_at` inside a horizon or already expired. |

Full URLs: `/api/v1/hr/documents/missing`, `/api/v1/hr/documents/expiring`.

## Data sources (normative)

| Concern | Source |
|---------|--------|
| What recruitment transferred (document-wise) | `candidate_handoff_snapshots.payload.documents` |
| What is required now | Document **ruleset** + `compute_candidate_checklist` (same matrix as recruitment handoff gate) |
| What exists / validity now | Live `documents` for the **candidate** linked to the accepted internal-HR handoff |
| Ownership / routing | `candidate_handoffs` (accepted, `destination = internal_hr`) + `workforce_employees` (`meta.internal_hr_handoff_id`) |
| Operational “what to do” | `activities` / checklist (referenced conceptually; optional linkage in later revisions) |

## Priority rules

### Missing

- **Definition:** `required_matrix − live_valid_documents = missing` (same notion as `missing_base_requirements` + ruleset checklist).
- **Snapshot role:** context only — e.g. was it already missing at handoff, was it reported as approved then, did state **worsen** after transfer (snapshot says `approved`, live is `expired` / absent).
- **Snapshot is not** used to decide “satisfied today”.

### Expiring

- **Definition:** live rows with `expires_at` (document `expire_date`) within `horizon_days` **or** already past today / status expired.
- **Snapshot is not** the source of current expiry; optional `snapshot_status` in response is historical context only.

## Filters

### `GET …/missing`

| Query | Notes |
|-------|--------|
| `assignee_scope` | `mine` \| `team` (default `mine`). Team = unscoped assignee filter for pool leads. |
| `document_type` | Canonical / alias normalized via `normalize_doc_type`. |
| `priority` | `high` = only **high-risk** types (see below). |
| `handoff_id` | Filter one handoff. |
| `candidate_id` | Filter one candidate. |
| `limit`, `offset` | Pagination over **queue rows** (one row per handoff × missing type). |

### `GET …/expiring`

| Query | Notes |
|-------|--------|
| `horizon_days` | `7` \| `30` \| `60` \| `90` (default `30`). |
| `status` | `expired` \| `expiring` \| `all` (default `all`). `expiring` = not expired by date but within horizon. |
| `document_type` | Optional filter. |
| `risk` | `high` = only high-risk types. |
| `assignee_scope` | `mine` \| `team`. |
| `limit`, `offset` | Pagination over queue rows (one row per live document in window). |

## High-risk document types (v1)

Canonical codes (after `normalize_doc_type`), aligned with transport compliance:

- `work_permit`
- `residence_permit`
- `visa`
- `code95`
- `tacho_card` (maps industry “driver card” / tachograph)
- `medical_certificate` (maps “medical exam” aliases)
- `psych_tests` (maps psychological / psychotest aliases)
- `driver_license` (included for operational driving compliance)

## Response item (v1)

Each queue row includes:

| Field | Meaning |
|-------|--------|
| `handoff_id` | Internal-HR handoff id. |
| `workforce_employee_id` | When materialized after accept. |
| `candidate_snapshot_summary` | Minimal identity from **snapshot** payload (`candidate.id` + name). |
| `document_type` | Canonical type. |
| `current_status` | Derived from **live** documents (or `missing`). |
| `required` | Whether type is in current required checklist (`missing` queue only; `true` for rows there). |
| `snapshot_status` | Status from snapshot document entry for that type, if any. |
| `expires_at` | ISO date from **live** document when relevant; `null` for pure missing rows. |
| `risk` | `high` \| `normal`. |
| `assignee_user_id` | From handoff (`assigned_to_user_id`) when set. |
| `recommended_action` | Short machine-oriented hint (`collect_required_document`, `urgent_collect_compliance_document`, `schedule_renewal`, `renew_or_replace_immediately`). |

Envelope: `{ "total": int, "items": [ … ] }`.

## Access control

Same as HR Inbox:

- Tenant session + **HR module enabled** (`require_hr_workforce_module_access`).
- Roles: `hr_officer` \| `administrator` \| `supervisor`.
- Recruiters and client roles: **403**.

## Scope note (v1 backend)

Queues are built over **accepted** internal-HR handoffs with an active candidate (deleted candidates excluded). Pending handoffs are out of scope for v1 document queues (workforce not materialized yet).

## Evolution

- Join open `activities` rows for deep-links.
- Company / own_company scoping refinements for multi-fleet tenants.
- Pagination pushed into SQL when row counts grow.
