# HR Dashboard Summary API

## Purpose

Aggregate read models for the **internal HR** workspace dashboard. The UI consumes these endpoints instead of ad‑hoc `Candidate` list queries so HR operational context stays aligned with **inbox**, **document queues**, and **HR task** semantics (and stays separate from recruitment funnels).

## Non-goals

- **No raw Candidate-driven dashboard.** Handlers must not scan `Candidate` for dashboard metrics. Use the services below only.
- No write operations on this surface.

## Data sources (authoritative)

| Concern | Service / module | Notes |
|--------|-------------------|--------|
| Pending / accepted internal HR handoffs | `backend.app.services.hr_inbox` (`list_internal_hr_handoffs_for_hr_inbox`) | `destination == internal_hr` only |
| Missing / expiring compliance documents | `backend.app.services.hr_documents_queue` (`list_hr_documents_missing`, `list_hr_documents_expiring`) | Ruleset + live docs; snapshot context where applicable |
| HR lane tasks (pending handoff + checklist) | `backend.app.services.reminder_tasks` (`list_reminders`, optional enrichments) | Filter tuple `HR_TASK_TYPES` and per-type string literals live in `backend.app.constants.hr_task_types` (shared with inbox, `/hr/tasks`, and handoff activity materialization). |
| SLA / risk scoring | `backend.app.services.hr_operational_risk` | Read-only; see `hr-operational-risk-layer.md` |

## RBAC and module access

Same stack as **`/api/v1/hr/*`** inbox and document queues:

1. `require_hr_workforce_module_access` — tenant `settings.modules.hr` must be enabled (superadmin bypasses).
2. `require_roles(Role.hr_officer, Role.administrator, Role.supervisor)` — **recruiter and other non‑HR roles receive 403** (administrator / superadmin bypass per existing `require_roles` rules).

## `schema_version`

- **`GET /summary`**, **`/workload`**, **`/compliance`**: **`schema_version`: `1`**
- **`GET /high-risk`**: **`schema_version`: `2`** — returns scored operational risk rows (see `hr-operational-risk-layer.md`), not the legacy document-queue row shape.

## Operational risk (read model)

SLA / risk scoring is implemented in `backend.app.services.hr_operational_risk` (read-only). It composes **inbox**, **document queues**, **HR reminder tasks**, **`candidate_handoffs`**, **`candidate_handoff_snapshots`**, and **`workforce_employees`** — not raw `Candidate` scans.

| Surface | Addition |
|---------|-----------|
| `GET /summary` | **`risk_summary`**: `total`, `counts_by_code`, `counts_by_severity`, `preview` (capped) |
| `GET /high-risk` | Full list of scored risk items (paginated), sorted by severity |

Details and risk codes: `docs/specs/architecture/hr-operational-risk-layer.md`.

## Caps and previews

- List previews (embedded in `GET /summary`): **5–10** items per block (implementation uses **8**).
- Dedicated list endpoints use sensible `limit` defaults (≤ **50**) with standard pagination where applicable.

## `assignee_scope`

Query parameter `assignee_scope=mine|team` (default **`team`** on the dashboard) mirrors HR document queues: **team** shows all assignees for roles `hr_officer`, `supervisor`, `administrator`, `superadmin`; **mine** restricts to the current user (with the same unassigned handoff pool rules as document queues).

## Endpoints

Mounted under **`/api/v1/hr/dashboard`**:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/summary` | Counts + previews + **`risk_summary`** (operational risk v1) |
| `GET` | `/high-risk` | Scored operational risk rows (`schema_version` **2**); optional `handoff_id`, `candidate_id`; `horizon_days` applies to document slices inside the risk engine. |
| `GET` | `/workload` | Open HR tasks grouped by `assignee_user_id` |
| `GET` | `/compliance` | Missing required documents grouped by `document_type` and by candidate (`candidate_id` + `handoff_id`) |

## References

- HR inbox queue: `docs/specs/architecture/hr-inbox-queue-api.md`
- HR document queues: `docs/specs/architecture/hr-documents-queue-api.md` (if present) / implementation in `hr_documents_queue.py`
- HR operational risk layer: `docs/specs/architecture/hr-operational-risk-layer.md`
