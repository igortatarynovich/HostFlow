# HR operational risk / SLA layer (v1)

Read-only classification on top of the internal-HR backbone. **No writes**: no new activities, no candidate/handoff mutations, no workforce edits from this layer.

## Non-goals

- **`Candidate` is not a source of truth** for these signals. The layer may read `candidate_handoffs`, `candidate_handoff_snapshots`, `workforce_employees`, and aggregates that already go through `hr_inbox` / `hr_documents_queue` / `reminder_tasks`.

## Implementation

| Module | Role |
|--------|------|
| `backend.app.services.hr_operational_risk` | Computes normalized risk rows and summary counts. |

## Risk codes (v1)

| `risk_code` | Condition (summary) | Default severity |
|-------------|---------------------|-------------------|
| `handoff_unaccepted_over_sla` | Internal-HR handoff `pending_review` and `requested_at` older than SLA hours | Escalates with age past SLA |
| `missing_high_risk_document` | Missing-queue row with transport / compliance **high** risk (see `HR_HIGH_RISK_DOC_TYPES`) | `critical` |
| `document_expired` | Live document in HR expiring queue with **expired** status | `critical` |
| `document_expiring_soon` | Live document expiring within **7** days | `low`–`high` by days left / doc risk |
| `onboarding_task_overdue` | HR lane activity (`HR_TASK_TYPES`) past `due_at` or status `overdue` | `low`–`high` by days late |
| `hr_inactivity` | Accepted internal-HR handoff, acceptance older than threshold, and linked `workforce_employees.updated_at` stale | `medium` |

## Thresholds (v1 constants)

Defined in `hr_operational_risk.py` (future: tenant/env overrides):

- `HANDOFF_UNACCEPTED_SLA_HOURS` — default **48**
- `HR_INACTIVITY_HOURS` — default **168** (7 days)
- `DOCUMENT_EXPIRING_SOON_DAYS` — default **7**

## Normalized risk row (API)

Each item includes:

- `risk_code`, `severity` (`low` \| `medium` \| `high` \| `critical`)
- `handoff_id` (optional if unknown)
- `workforce_employee_id` (when applicable)
- `candidate_snapshot` — minimal identity from snapshot / queue summary (not live candidate)
- `reason`, `recommended_action`
- `due_at` / `expires_at` (when applicable)
- `document_type`, `task_id` — optional anchors for UI

## Dashboard integration

| Endpoint | Behaviour |
|----------|-----------|
| `GET /api/v1/hr/dashboard/summary` | Adds `risk_summary` (`total`, `counts_by_code`, `counts_by_severity`, `preview`). `schema_version` remains **1**. |
| `GET /api/v1/hr/dashboard/high-risk` | Returns paginated **scored** risk rows (all codes), sorted by severity then dates. `schema_version` is **2** (replaces legacy raw document-queue DTO on this route). |

## Worker dispatch (alerts, v1)

Operational **notifications** are not emitted from dashboard reads. A scheduled worker closes the loop **risk → alerts**:

| Entry | Role |
|-------|------|
| `backend.app.jobs.hr_operational_alerts_dispatch` | `dispatch_hr_operational_alerts_for_tenant` / `dispatch_hr_operational_alerts_all_tenants` — uses `tenant_enforced_session` (RLS + `security_job_context`), then `dispatch_hr_operational_alerts`. |
| `backend/scripts/dispatch_hr_operational_alerts.py` | CLI wrapper (no HTTP): default **dry-run**; pass `--apply` to send in-app notifications. |

Synthetic viewer: if `--viewer-id` / `--viewer-role` are omitted, the job picks one active user per tenant among `superadmin`, `administrator`, `hr_officer`, `supervisor` (preferring superadmin → administrator → hr_officer → supervisor) so `list_operational_risk_items` runs with the same **team** scope semantics as the HR dashboard.

Audit actor id defaults to `system:hr_operational_alerts_dispatch` or override via env `HR_OPERATIONAL_ALERTS_ACTOR_ID` / CLI `--actor-id`.

Details: `docs/specs/architecture/hr-operational-alerts-layer.md`.

## References

- Dashboard spec: `docs/specs/architecture/hr-dashboard-summary-api.md`
- HR task type constants: `backend/app/constants/hr_task_types.py`
- Alerts layer: `docs/specs/architecture/hr-operational-alerts-layer.md`
