# Operational metrics — canonical registry

> Status: living document. Closes G-3 from `docs/specs/operations-loop.md`.
>
> Owner: backend platform.
> Updated when a new dashboard widget is added, when a metric definition changes,
> or when a drilldown URL changes.

## 1. Why this document exists

We had bugs where the dashboard said "Stuck leads = 12" but clicking the widget
opened a list with 47 rows (or 0). The numbers and the lists came from
different code paths, with different scopes (user vs tenant), different
"what counts as stuck" definitions, and different "is candidate operationally
silent" filters.

Every operational metric exposed in the UI **must** be backed by an entry in
this registry. The entry pins down:

- **What** the number means (one-sentence definition + SQL fingerprint).
- **Who** it is scoped to (logged-in user / team / tenant).
- **Where** it comes from (backend endpoint + field name).
- **How** to drill down (frontend route + exact query parameters that produce
  the same set of rows the number was computed from).

The CI test `tests/test_metric_drilldown_consistency.py` enforces:

1. Each metric in the registry has a frontend route present in the
   generated route table (`crmAppPaths.generated.ts`) — drilldown is reachable.
2. The drilldown URL is well-formed (parsable, all `key=value` pairs lower-cased,
   no whitespace).
3. Metrics flagged `parity:strict` have a **count parity** (the backend list
   endpoint returns the same `total` as the dashboard counter would compute on
   the same fixture).

## 2. Universal contract

Every metric MUST:

- **Apply the G-2 silenced-candidate filter by default** (rows tied to candidates
  in `PIPELINE_COMPLETED_STAGE_CODES` or `deleted_at IS NOT NULL` are excluded
  from both the count and the drilldown unless the metric is explicitly about
  terminal candidates — e.g. "Rejected this month").
- **Apply the same scope filter to the count and the drilldown.** A user-scoped
  count never links to a tenant-wide list. A tenant-wide count always links to
  the team-scope drilldown (with `assignee_scope=team` or its equivalent).
- **Document the time window**, if any, in the same way for both sides
  (`due_lt=now`, `created_gte=...`, etc).

## 3. Registry

Columns:

| field | meaning |
|-------|---------|
| `id` | stable slug used by the test |
| `label` | UI label (i18n key recommended) |
| `source` | backend endpoint + field |
| `definition` | one-sentence definition |
| `scope` | `user` / `team` / `tenant` |
| `drilldown` | frontend route + canonical query string |
| `silenced_filter` | `default` (G-2 applies) / `terminal_only` (the metric *is* about terminal rows) |
| `parity` | `strict` (test enforces count = drilldown.total) / `informational` |

### 3.1 Operations counters (`/analytics/ops-counters`)

| id | label | source | definition | scope | drilldown | silenced_filter | parity |
|----|-------|--------|------------|-------|-----------|-----------------|--------|
| `ops.no_next_action_candidates` | `app.dashboard.ops.no_next_action_candidates` | `GET /analytics/ops-counters` → `no_next_action_candidates` | Active candidates whose owner has no pending reminder of any type. | user | `/app/candidates?next_action=missing&assignee=me` | `default` | `strict` |
| `ops.leads_no_next_action` | `app.dashboard.ops.leads_no_next_action` | `GET /analytics/ops-counters` → `leads_no_next_action` | Processed leads with no active reminder. | tenant | `/app/leads?next_action=missing` | `default` | `strict` |
| `ops.leads_sla_no_next_action_reminders` | `app.dashboard.ops.leads_sla_no_next_action` | `GET /analytics/ops-counters` → `leads_sla_no_next_action_reminders` | Active reminders of type `leads_no_next_action` for the **logged-in user**. | user | `/app/tasks?type=leads_no_next_action&assignee_scope=mine` | `default` | `strict` |
| `ops.leads_sla_stuck_stage_reminders` | `app.dashboard.ops.leads_stuck_stage` | `GET /analytics/ops-counters` → `leads_sla_stuck_stage_reminders` | Active reminders of type `leads_stuck_stage` for the **logged-in user**. | user | `/app/tasks?type=leads_stuck_stage&assignee_scope=mine` | `default` | `strict` |

> **Common bug fixed by entries above:** the dashboard previously showed a
> tenant-wide stuck-leads count linking to a user-scoped list. Either both
> sides are user-scoped or both tenant-wide; mixing is forbidden by parity test.

### 3.2 Handoff (`/analytics/handoff-stats`)

The endpoint returns aggregated counters over a date range (`requested_at` ∈ [from, to]).
The dashboard widgets pin them to `period=ytd` by default.

| id | label | source | definition | scope | drilldown | silenced_filter | parity |
|----|-------|--------|------------|-------|-----------|-----------------|--------|
| `handoff.requested` | `app.dashboard.handoff.requested` | `GET /analytics/handoff-stats` → `total_requested` | Handoffs initiated in the period (any status). | tenant | `/app/candidates?handoff_status=any` | `default` | `informational` |
| `handoff.accepted` | `app.dashboard.handoff.accepted` | `GET /analytics/handoff-stats` → `total_accepted` | Handoffs accepted by the client (candidate now in client pipeline). | tenant | `/app/candidates?handoff_status=accepted` | `default` | `strict` |
| `handoff.rejected` | `app.dashboard.handoff.rejected` | `GET /analytics/handoff-stats` → `total_rejected` | Handoffs rejected by the client. | tenant | `/app/candidates?handoff_status=rejected` | `terminal_only` | `strict` |
| `handoff.returned` | `app.dashboard.handoff.returned` | `GET /analytics/handoff-stats` → `total_returned` | Handoffs returned by the client to the agency. | tenant | `/app/candidates?handoff_status=returned` | `default` | `strict` |
| `handoff.pending` | `app.dashboard.handoff.pending` | `GET /analytics/handoff-stats` → derived: `total_requested − total_accepted − total_rejected − total_returned` | Handoffs awaiting a client decision (no terminal status yet). | tenant | `/app/candidates?handoff_status=pending` | `default` | `strict` |

### 3.3 Documents (`/analytics/document-stats`)

| id | label | source | definition | scope | drilldown | silenced_filter | parity |
|----|-------|--------|------------|-------|-----------|-----------------|--------|
| `documents.missing` | `app.dashboard.documents.missing` | `GET /analytics/document-stats` → `missing` | Active candidates with at least one required document missing. | tenant | `/app/documents?quick=missing` | `default` | `informational` |
| `documents.in_progress` | `app.dashboard.documents.in_progress` | `GET /analytics/document-stats` → `in_progress` | Documents in workflow (uploaded, awaiting verification). | tenant | `/app/documents?quick=in_progress` | `default` | `informational` |
| `documents.ready` | `app.dashboard.documents.ready` | `GET /analytics/document-stats` → `ready` | Documents passed all checks. | tenant | `/app/documents?quick=ready` | `default` | `informational` |
| `documents.rejected` | `app.dashboard.documents.rejected` | `GET /analytics/document-stats` → `rejected` | Documents rejected by verifier. | tenant | `/app/documents?status=rejected` | `default` | `informational` |

### 3.4 Funnel & stages (`/analytics/funnel`, `/analytics/stage-metrics`)

| id | label | source | definition | scope | drilldown | silenced_filter | parity |
|----|-------|--------|------------|-------|-----------|-----------------|--------|
| `funnel.stage_count` | `app.dashboard.funnel.stage_count.<stage>` | `GET /analytics/funnel` → `stages[].count` | Active candidates in `<stage>` (single stage code). | tenant | `/app/candidates?stage=<stage>` | `default` | `strict` |
| `funnel.rejected_by_reason` | `app.dashboard.funnel.rejected_by_reason.<reason>` | `GET /analytics/funnel` → reason histogram | Rejected candidates grouped by `status_reason` code. | tenant | `/app/candidates?stage=rejected&status_reason=<reason>` | `terminal_only` | `informational` |
| `funnel.declined_by_reason` | `app.dashboard.funnel.declined_by_reason.<reason>` | `GET /analytics/funnel` → reason histogram | Declined candidates grouped by `status_reason` code. | tenant | `/app/candidates?stage=declined&status_reason=<reason>` | `terminal_only` | `informational` |

### 3.5 Risk intelligence (`/analytics/risk-intelligence`)

| id | label | source | definition | scope | drilldown | silenced_filter | parity |
|----|-------|--------|------------|-------|-----------|-----------------|--------|
| `risk.critical` | `app.dashboard.risk.critical` | `GET /analytics/risk-intelligence` → `critical[]` | Candidates flagged with risk level `critical` by the v1 risk engine. | tenant | `/app/candidates?risk_level=critical` | `default` | `informational` |
| `risk.high` | `app.dashboard.risk.high` | `GET /analytics/risk-intelligence` → `high[]` | Candidates flagged with risk level `high`. | tenant | `/app/candidates?risk_level=high` | `default` | `informational` |

### 3.6 Communications SLA (`/communications/sla/incidents`)

| id | label | source | definition | scope | drilldown | silenced_filter | parity |
|----|-------|--------|------------|-------|-----------|-----------------|--------|
| `comms.sla_overdue_user` | `app.dashboard.comms.sla_overdue_user` | `GET /communications/sla/incidents?assignee_scope=mine` → `total` | Communication threads past SLA assigned to me. | user | `/app/communications/sla?assignee_scope=mine` | `default` | `strict` |
| `comms.sla_overdue_team` | `app.dashboard.comms.sla_overdue_team` | `GET /communications/sla/incidents` → `total` | Communication threads past SLA, tenant-wide. | tenant | `/app/communications/sla` | `default` | `strict` |

## 4. Adding a new metric — checklist

When adding a new dashboard widget:

1. Add a row in section 3.x above (the registry).
2. Add a fixture entry in `tests/test_metric_drilldown_consistency.py::REGISTRY`.
3. Make sure the backend endpoint applies the same scope filter as the
   drilldown route does on the frontend.
4. Make sure `silenced_filter=default` metrics use the
   `exclude_completed_candidate_entities_clause` from
   `backend/app/services/candidate_lifecycle.py` (or are layered on top of an
   endpoint that already does).
5. Run `pytest tests/test_metric_drilldown_consistency.py` — this is a fast
   structural check, not a data check.

## 5. Out of scope (intentionally)

- Per-tenant data parity (e.g. *running* the count and the list against the
  same DB and asserting equality). That belongs in integration tests once we
  have a stable seed dataset. We track that as a follow-up after G-3.
- Aggregation across multiple endpoints (e.g. "Total work on my desk =
  reminders + threads + handoffs"). Composite metrics are documented as
  separate entries with their decomposition spelled out.
