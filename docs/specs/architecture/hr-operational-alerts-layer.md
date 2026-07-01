# HR operational alerts (v1)

Read/react layer **above** `hr_operational_risk`: maps classified risks to **in-app notifications**
with **throttling / dedupe**, plus an **audit trail**. Intended for **workers / cron**, not for
`GET /hr/dashboard/*` (avoids spamming users on every UI refresh).

## Implementation

| Module | Role |
|--------|------|
| `backend.app.services.hr_operational_alerts` | Risk → recipients → `create_notification` + `log_activity` |

## Behaviour

1. **Input**: reuses `list_operational_risk_items` (same RBAC/scope inputs as risk: `tenant_id`, `viewer_id`, `viewer_role`, `assignee_scope`, `horizon_days`).
2. **Recipients (v1 heuristics)**  
   - Compliance (`missing_high_risk_document`, `document_expired`): HR officers + supervisors + document assignee (if any).  
   - `document_expiring_soon`: assignee; if severity high/critical also HR; if no assignee, HR pool.  
   - `handoff_unaccepted_over_sla`: supervisors + assignee + HR for high/critical; else assignee + HR.  
   - `onboarding_task_overdue`: activity assignee, else HR pool.  
   - `hr_inactivity`: HR + supervisors + handoff assignee.
3. **Notifications**  
   - One stable **`related_entity_type`**: `hr_operational_alert`.  
   - **`related_entity_id`**: SHA-256(`tenant_id` + fingerprint) truncated to 36 chars.  
   - **Service pre-check**: before `create_notification`, query for an existing row for the same
     `(tenant, user, event_type, related_entity_type, related_entity_id)` inside the throttle window.
     This avoids duplicate inserts when the user’s bell already has >50 newer unrelated rows (the
     built-in dedupe scan inside `create_notification` only looks at the latest 50).  
   - Payload still carries `handoff_id`, `risk_code`, `severity`, **`dedupe_key`** (fingerprint), etc.
4. **Throttle**: `dedupe_window_minutes` scales with severity (see module constants).
5. **Audit**: `log_activity` with `hr_operational_alert_dispatch` (per attempt) and `hr_operational_alert_dry_run` (single summary when `dry_run=True`).

## API surface

No HTTP route in v1. Production dispatch:

| Mechanism | Notes |
|-----------|--------|
| `backend.app.jobs.hr_operational_alerts_dispatch` | Import `dispatch_hr_operational_alerts_all_tenants` or `dispatch_hr_operational_alerts_for_tenant` from workers (APScheduler, Celery, etc.). |
| `python backend/scripts/dispatch_hr_operational_alerts.py` | CLI: **dry-run by default**; `--apply` performs notification writes. Logs start/end and aggregate counts at INFO. |

Both use `tenant_enforced_session` (see `backend.app.db.deps`) so Postgres RLS matches API paths. Re-runs are safe: throttling + fingerprint + service pre-check (see above).

## References

- Risk read model: `docs/specs/architecture/hr-operational-risk-layer.md`
- Notifications dedupe: `backend.app.services.user_notifications.create_notification`
