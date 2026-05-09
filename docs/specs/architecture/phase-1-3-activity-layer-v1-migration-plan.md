# Phase 1.3 — `activity_layer_v1` migration plan

> **Status:** ACCEPTED (with constraints, 2026-05-09). Implementation may
> proceed; the migration revision and the model rewire ship together but
> stay behind the feature flag `ENABLE_ACTIVITY_LAYER_V1` until the
> §15 approval checklist is green and the §12 staging canary passes.

## Constraints (binding)

These six constraints were applied during review and are **not negotiable**
when implementing the revision:

1. **`NotificationSeverity` is `info | warning | critical`** — exactly three
   values. No `error` tier (would overlap `critical`). See §6.3 for the
   `priority → severity` collapse map.
2. **`company_id` backfill never guesses.** Order is: (1) explicit value
   from `payload`/`metadata`, (2) related-entity FK chase, (3) tenant
   default *only when unique*, (4) leave NULL. A wrong `company_id`
   creates cross-tenant bleeding bugs that are far worse than a NULL
   filter row in the UI.
3. **`activity_id` linkage is high-confidence-only.** No 24-hour
   bucket, no fuzzy text matching, no "most recent activity on the same
   entity". Allowed evidence is: explicit `activity_id`/`reminder_id` in
   `payload`, or strict `(tenant, related_entity, type-pair, ≤ 5 min)`
   match. Phase 1.3 acceptance is `notifications_activity_id_linked_pct
   ≥ 50 %`; the ≥ 80 % target is deferred to Phase 2/3 once producers
   write `activity_id` directly.
4. **`payload` synonym is kept until Phase 4.** Removing it before the
   service layer migration (Phase 2) would silently break in-flight
   workers. The synonym lives on the ORM models for at least two
   release cycles.
5. **`in_progress` is forward-only.** On downgrade we audit the rows
   that hold `in_progress` and collapse them to `pending`; we do not
   attempt to recover the original semantic.
6. **Compat views are temporary.** `reminders` and `user_notifications`
   views exist only for the deploy-window safety of in-flight workers;
   frontend, Phase 2 API and any new code MUST NOT depend on them.
   Phase 2 is responsible for removing every legacy-name read.
>
> **Scope:** rename of `reminders` → `activities`, `reminder_events` →
> `activity_events`, `user_notifications` → `notifications`, plus the
> additive columns required by the canon model. All other Phase 1 work
> (1.0 calendar baseline, 1.1 Activity / ActivityEvent aliases, 1.2
> Notification alias) is **already merged**, see
> `backend/alembic/versions/202607150001_calendar_tables_explicit.py`,
> `backend/app/models/activity.py`, `backend/app/models/activity_event.py`,
> `backend/app/models/notification.py`, `backend/app/models/__init__.py`.
>
> **Depends on:**
> - [`ADR-012`](./ADR-012-activity-notification-operating-layer.md)
> - [`activity-notification-operating-layer.md`](./activity-notification-operating-layer.md) (canon)
> - [`activities.md`](../workflows/activities.md) §4.4 *Status mapping*
> - [`activities-sla-matrix.md`](../workflows/activities-sla-matrix.md)

---

## 0. Why this is a separate, gated step

Phase 1.0–1.2 were **strictly additive**: a new Alembic baseline for
`calendar_*` tables and three import-only aliases (`Activity = Reminder`,
`ActivityEvent = ReminderEvent`, `Notification = UserNotification`). Nothing
in the live database changed.

Phase 1.3 is a different beast:

- It **renames live tables** that hold the operational inbox of every
  tenant (every reminder, every notification ever delivered).
- It **adds NOT NULL columns** that need to be backfilled from data that
  is currently scattered across other tables (e.g. `company_id`).
- It **collapses three legacy status values** (`new`, `pending`, `sent`)
  into one canonical value (`planned`). That mapping is irreversible
  without auditing — see §6.
- It is the precondition for Phase 2 (HTTP API consolidation), so any bug
  here blocks the whole rollout.

For these reasons we treat Phase 1.3 as a **separate, named migration
revision** (`activity_layer_v1`) with: explicit DDL, deterministic backfill,
documented rollback, canary on staging, observable success criteria.

---

## 1. End state targeted by this migration

After successful upgrade to `activity_layer_v1` head:

| Old (Phase 1 entry state) | New |
|---|---|
| `reminders`             | `activities` |
| `reminder_events.reminder_id` | `activity_events.activity_id` |
| `reminder_events`        | `activity_events` |
| `user_notifications`    | `notifications` |
| `Reminder.type`          | `activities.type` (kept; just renamed table) |
| `Reminder.entity_type` / `entity_id` | `activities.related_entity_type` / `related_entity_id` (renamed) |
| `Reminder.assignee_id`  | `activities.assigned_to_user_id` |
| `Reminder.created_by`   | `activities.created_by_user_id` |
| `UserNotification.event_type` | `notifications.type` |
| `UserNotification.entity_type` / `entity_id` | `notifications.related_entity_type` / `related_entity_id` |

New columns added (NULL initially, backfilled in §6):

`activities`:
- `company_id           VARCHAR(36)  NULL`  → indexed
- `source_module        VARCHAR(64)  NULL`  → derived from legacy `source` + `entity_type`
- `starts_at            TIMESTAMPTZ  NULL`
- `reminder_at          TIMESTAMPTZ  NULL`  → already exists as `remind_at`; renamed in this same migration
- `sla_due_at           TIMESTAMPTZ  NULL`
- `sla_status           VARCHAR(16)  NULL`
- `metadata             JSONB        NULL`  → renamed from `payload`

`notifications`:
- `title                VARCHAR(256) NULL`  → backfilled from `payload.title` or templated
- `body                 TEXT         NULL`  → backfilled from `payload.body` or templated
- `severity             VARCHAR(16)  NULL`  → backfilled from `priority` + `event_type`
- `activity_id          VARCHAR(36)  NULL`  → cannot be backfilled retroactively (see §10); always NULL for legacy rows
- `metadata             JSONB        NULL`  → renamed from `payload`
- `is_read`             — already present (no change)

**No columns are dropped in `activity_layer_v1`.** Removal of legacy
columns (e.g. the `assignee_id` after `assigned_to_user_id` is populated)
is gated to Phase 4 cleanup (its own ADR-012 follow-up revision) so we
keep a rollback path for at least two release cycles.

---

## 2. DDL — exact statements

The migration runs as **two top-level transactions** so a partial failure
in `notifications` does not roll back the `activities` rename:

### 2.1 Transaction A — `activities`

```sql
-- Phase 1.3.A.1 — rename table
ALTER TABLE reminders        RENAME TO activities;
ALTER TABLE reminder_events  RENAME TO activity_events;

-- Phase 1.3.A.2 — rename FK column on activity_events
ALTER TABLE activity_events  RENAME COLUMN reminder_id TO activity_id;

-- Phase 1.3.A.3 — rename core columns on activities
ALTER TABLE activities       RENAME COLUMN entity_type      TO related_entity_type;
ALTER TABLE activities       RENAME COLUMN entity_id        TO related_entity_id;
ALTER TABLE activities       RENAME COLUMN assignee_id      TO assigned_to_user_id;
ALTER TABLE activities       RENAME COLUMN created_by       TO created_by_user_id;
ALTER TABLE activities       RENAME COLUMN remind_at        TO reminder_at;
ALTER TABLE activities       RENAME COLUMN payload          TO metadata;

-- Phase 1.3.A.4 — additive columns (NULL until backfill)
ALTER TABLE activities  ADD COLUMN company_id    VARCHAR(36);
ALTER TABLE activities  ADD COLUMN source_module VARCHAR(64);
ALTER TABLE activities  ADD COLUMN starts_at     TIMESTAMPTZ;
ALTER TABLE activities  ADD COLUMN sla_due_at    TIMESTAMPTZ;
ALTER TABLE activities  ADD COLUMN sla_status    VARCHAR(16);

-- Phase 1.3.A.5 — recreate / rename indexes (Postgres auto-renames PK; secondary
-- indexes are renamed by `ALTER INDEX … RENAME TO …`).
ALTER INDEX ix_reminders_tenant_due       RENAME TO ix_activities_tenant_due;
ALTER INDEX ix_reminders_entity           RENAME TO ix_activities_related_entity;
ALTER INDEX ix_reminders_assignee_remind  RENAME TO ix_activities_assignee_reminder;
ALTER INDEX ix_reminders_assignee_due     RENAME TO ix_activities_assignee_due;
ALTER INDEX ix_reminders_status_due       RENAME TO ix_activities_status_due;
ALTER INDEX ix_reminder_events_tenant     RENAME TO ix_activity_events_tenant;
ALTER INDEX ix_reminder_events_reminder   RENAME TO ix_activity_events_activity;

-- Phase 1.3.A.6 — new indexes for the new columns
CREATE INDEX ix_activities_tenant_company   ON activities (tenant_id, company_id)             WHERE company_id IS NOT NULL;
CREATE INDEX ix_activities_tenant_source    ON activities (tenant_id, source_module);
CREATE INDEX ix_activities_tenant_sla       ON activities (tenant_id, sla_status, sla_due_at) WHERE sla_status IS NOT NULL;
CREATE INDEX ix_activities_tenant_starts    ON activities (tenant_id, starts_at)              WHERE starts_at IS NOT NULL;
```

### 2.2 Transaction B — `notifications`

```sql
ALTER TABLE user_notifications RENAME TO notifications;
ALTER TABLE notifications  RENAME COLUMN event_type   TO type;
ALTER TABLE notifications  RENAME COLUMN entity_type  TO related_entity_type;
ALTER TABLE notifications  RENAME COLUMN entity_id    TO related_entity_id;
ALTER TABLE notifications  RENAME COLUMN payload      TO metadata;

ALTER TABLE notifications  ADD COLUMN title       VARCHAR(256);
ALTER TABLE notifications  ADD COLUMN body        TEXT;
ALTER TABLE notifications  ADD COLUMN severity    VARCHAR(16);
ALTER TABLE notifications  ADD COLUMN activity_id VARCHAR(36);

ALTER INDEX ix_user_notifications_tenant_id  RENAME TO ix_notifications_tenant_id;
ALTER INDEX ix_user_notifications_user_id    RENAME TO ix_notifications_user_id;
ALTER INDEX ix_user_notifications_event_type RENAME TO ix_notifications_type;
ALTER INDEX ix_user_notifications_priority   RENAME TO ix_notifications_severity_legacy;

CREATE INDEX ix_notifications_tenant_severity_unread
    ON notifications (tenant_id, severity, is_read)
    WHERE is_read = false;
CREATE INDEX ix_notifications_tenant_activity
    ON notifications (tenant_id, activity_id)
    WHERE activity_id IS NOT NULL;
CREATE INDEX ix_notifications_tenant_related_entity
    ON notifications (tenant_id, related_entity_type, related_entity_id);
```

> Index name normalisation matters: the new names match the canon and let
> us drop the legacy `ix_user_notifications_*` aliases in Phase 4.

### 2.3 Compatibility view — temporary, read-only

> **Constraint #6.** Compat views exist **only** for the deploy-window
> safety of in-flight workers that started before the rolling restart
> picked up the new code. They are **not a long-term API**. Frontend
> MUST NOT use them, Phase 2 API MUST NOT read from them, and any new
> code that hits them is a bug. Phase 2 is responsible for ripping out
> every legacy-name read; Phase 4 drops the views.

```sql
CREATE VIEW reminders          AS SELECT * FROM activities;
CREATE VIEW user_notifications AS SELECT * FROM notifications;
```

Read-only by construction (`SELECT *` from a single table is auto-updateable
in Postgres, so we explicitly add `WITH READ ONLY` semantics by attaching
INSTEAD OF triggers that raise an exception):

```sql
CREATE OR REPLACE FUNCTION _reject_legacy_write() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
      'Write to legacy view %I is not allowed — write to the canonical table',
      TG_TABLE_NAME
      USING HINT = 'See ADR-012 / Phase 1.3 plan §2.3';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER reject_writes_reminders
  INSTEAD OF INSERT OR UPDATE OR DELETE ON reminders
  FOR EACH ROW EXECUTE FUNCTION _reject_legacy_write();

CREATE TRIGGER reject_writes_user_notifications
  INSTEAD OF INSERT OR UPDATE OR DELETE ON user_notifications
  FOR EACH ROW EXECUTE FUNCTION _reject_legacy_write();
```

This makes the constraint observable: any write attempt against the
legacy name surfaces as a failed query in Datadog within seconds, so we
can pinpoint and migrate the offending caller before Phase 2 closes.
The views and the trigger function are **dropped in Phase 4 cleanup**.

---

## 3. Status mapping (`activities.status`)

Legacy `reminders.status` values:

| Legacy | Canonical (Phase 1.3) | Reason |
|---|---|---|
| `new`        | `planned`     | identical semantics — created, not started |
| `pending`    | `planned`     | "scheduled, waiting for due_at" → planned |
| `sent`       | `planned`     | "notification was emitted, but task is open" → still planned |
| `overdue`    | `overdue`     | identical |
| `done`       | `done`        | identical |
| `cancelled`  | `cancelled`   | identical |

The introduction of `in_progress` is **forward-only**: the migration does
not retroactively try to detect "in progress" from legacy data. Old rows
remain on `planned` / `overdue`; new code assigns `in_progress` when the
operator explicitly clicks *Start*.

Backfill SQL:

```sql
UPDATE activities SET status = 'planned'
WHERE status IN ('new', 'pending', 'sent');
```

This UPDATE is **idempotent** and uses the existing
`ix_activities_status_due` index. We do **not** add a CHECK constraint in
this revision — that lands in Phase 4 once we have telemetry confirming
no legacy producer still writes the old values.

---

## 4. Backfill — `activities.company_id`

> **Constraint #2.** `company_id` backfill **never guesses**. A wrong
> `company_id` is worse than a NULL row — it puts an activity into the
> wrong tenant scope and leaks across UI filters. We use four strict
> sources, in this order, and stop at the first match. If none match,
> the row stays NULL.

### 4.1 Source 1 — explicit value from `metadata` (highest confidence)

If the producer already wrote `company_id` into the JSON payload, trust it.

```sql
UPDATE activities
   SET company_id = (metadata->>'company_id')
 WHERE company_id IS NULL
   AND metadata ? 'company_id'
   AND metadata->>'company_id' ~ '^[0-9a-fA-F-]{36}$';  -- UUID shape only
```

### 4.2 Source 2 — direct company-typed link

```sql
UPDATE activities
   SET company_id = related_entity_id
 WHERE company_id IS NULL
   AND related_entity_type = 'company'
   AND related_entity_id ~ '^[0-9a-fA-F-]{36}$';
```

### 4.3 Source 3 — related-entity FK chase

Each branch is **one** UPDATE, idempotent, gated on `company_id IS NULL`.
Joins use the canonical FK; if the entity itself has a NULL `company_id`,
the activity stays NULL (we don't fall back further).

```sql
UPDATE activities a
   SET company_id = l.company_id
  FROM leads l
 WHERE a.related_entity_type = 'lead'
   AND a.related_entity_id   = l.id
   AND a.company_id IS NULL
   AND l.company_id IS NOT NULL;

UPDATE activities a
   SET company_id = c.company_id
  FROM candidates c
 WHERE a.related_entity_type = 'candidate'
   AND a.related_entity_id   = c.id
   AND a.company_id IS NULL
   AND c.company_id IS NOT NULL;

UPDATE activities a
   SET company_id = ct.company_id
  FROM communication_threads ct
 WHERE a.related_entity_type = 'communication_thread'
   AND a.related_entity_id   = ct.id
   AND a.company_id IS NULL
   AND ct.company_id IS NOT NULL;

UPDATE activities a
   SET company_id = so.company_id
  FROM service_orders so
 WHERE a.related_entity_type = 'service_order'
   AND a.related_entity_id   = so.id::text
   AND a.company_id IS NULL
   AND so.company_id IS NOT NULL;

UPDATE activities a
   SET company_id = i.company_id
  FROM invoices i
 WHERE a.related_entity_type = 'invoice'
   AND a.related_entity_id   = i.id::text
   AND a.company_id IS NULL
   AND i.company_id IS NOT NULL;
```

### 4.4 Source 4 — tenant default, **only when unique**

For tenants that own **exactly one** company, fall back to that company.
This is the "no ambiguity" guarantee: as soon as a tenant has two or
more companies, we leave the row NULL.

```sql
WITH unique_company AS (
    SELECT tenant_id, company_id
      FROM (
          SELECT c.tenant_id,
                 c.id AS company_id,
                 COUNT(*) OVER (PARTITION BY c.tenant_id) AS company_count
            FROM companies c
           WHERE c.deleted_at IS NULL
      ) s
     WHERE s.company_count = 1
)
UPDATE activities a
   SET company_id = uc.company_id
  FROM unique_company uc
 WHERE a.tenant_id   = uc.tenant_id
   AND a.company_id IS NULL;
```

### 4.5 Anything else stays NULL

We do **not** sample, infer from `assignee_id`, or scan history. NULL
is the correct value when none of the four sources resolved it.

**Acceptance:** §11 reports `activities_company_id_null` before/after
backfill plus a per-source histogram (rows resolved by source 1, 2, 3,
4). Phase 1.3 does not block on a high NULL count — Phase 4 enforces
NOT NULL only after Phase 2 (producers) and Phase 3 (frontend) have
caught up. The §11 thresholds are **observability targets**, not
hard gates.

`company_id` is **NOT NULL-enforced** only in Phase 4 cleanup, **never**
in 1.3. Leaving it nullable here is intentional: it preserves rows whose
related entity was deleted before the migration ran, and it lets us
ship 1.3 without a hard data dependency on the order in which other
Phase 1 cleanups happen.

---

## 5. Backfill — `activities.source_module`

Derived from a small lookup table over `(related_entity_type, source, type)`:

```sql
UPDATE activities SET source_module = CASE
    WHEN related_entity_type = 'lead'                  THEN 'leads'
    WHEN related_entity_type = 'candidate'             THEN 'recruitment'
    WHEN related_entity_type = 'communication_thread'  THEN 'communications'
    WHEN related_entity_type = 'service_order'         THEN 'services'
    WHEN related_entity_type = 'invoice'               THEN 'invoicing'
    WHEN related_entity_type = 'company'               THEN 'crm'
    WHEN related_entity_type = 'workforce_employee'    THEN 'hr'
    WHEN type LIKE 'document\_%'                       THEN 'documents'  -- escaped underscore
    WHEN type LIKE 'uos\_%'                            THEN 'recruitment'
    ELSE 'unknown'
END
WHERE source_module IS NULL;
```

The `'unknown'` bucket is **observable** in §11 and should be
investigated post-migration; the column stays nullable in 1.3, so it does
not block the migration if some classifier is wrong.

---

## 6. Backfill — `notifications.title` / `body` / `severity`

Legacy `user_notifications` has `event_type` + `payload` JSON only.
Title/body must be derived deterministically.

### 6.1 Title

```sql
UPDATE notifications SET title = COALESCE(
    metadata->>'title',
    metadata->>'subject',
    -- fallback templated by event type
    CASE type
        WHEN 'reminder_due'              THEN 'Reminder due'
        WHEN 'reminder_overdue'          THEN 'Reminder overdue'
        WHEN 'lead_assigned'             THEN 'New lead assigned'
        WHEN 'candidate_assigned'        THEN 'New candidate assigned'
        WHEN 'document_expiring'         THEN 'Document expiring soon'
        WHEN 'document_expired'          THEN 'Document expired'
        WHEN 'communication_inbound'     THEN 'New inbound message'
        WHEN 'sla_warning'               THEN 'SLA warning'
        WHEN 'sla_breached'              THEN 'SLA breached'
        ELSE INITCAP(REPLACE(type, '_', ' '))
    END
)
WHERE title IS NULL;
```

### 6.2 Body

```sql
UPDATE notifications SET body = COALESCE(
    metadata->>'body',
    metadata->>'message',
    metadata->>'description'
)
WHERE body IS NULL;
-- intentionally leaves body NULL when no source text exists; UI must handle NULL.
```

### 6.3 Severity (priority → severity)

> **Constraint #1.** Closed enumeration is `info | warning | critical`.
> Legacy producers that wrote `error`, `high`, `urgent` etc. into
> `priority` are collapsed onto these three values: anything that is
> "this caused or will cause harm" becomes `critical`, anything that is
> "needs attention but not yet harmful" becomes `warning`, the rest is
> `info`. We deliberately have no `error` tier — see ADR-012 §6 and the
> canon §3.3.

```sql
UPDATE notifications SET severity = CASE
    -- Critical: something is broken / SLA breached / hard deadline missed
    WHEN priority IN ('critical', 'urgent', 'p0')         THEN 'critical'
    WHEN priority IN ('error', 'high', 'p1')              THEN 'critical'
    -- inferred from type when priority is NULL
    WHEN type LIKE '%\_breached'                          THEN 'critical'
    WHEN type LIKE '%\_expired'                           THEN 'critical'
    WHEN type LIKE '%\_failed'                            THEN 'critical'

    -- Warning: needs attention, not yet harmful (overdue, SLA at risk, expiring)
    WHEN priority IN ('medium', 'normal', 'p2', 'warn', 'warning')  THEN 'warning'
    WHEN type LIKE '%\_overdue'                           THEN 'warning'
    WHEN type LIKE '%\_warning'                           THEN 'warning'
    WHEN type LIKE '%\_expiring'                          THEN 'warning'
    WHEN type LIKE '%\_at_risk'                           THEN 'warning'

    -- Info: everything else
    ELSE 'info'
END
WHERE severity IS NULL;
```

The legacy `priority` column is **kept** in 1.3 — Phase 4 cleanup drops
it once producers are confirmed to write `severity` directly. The
mapping is one-way: rows in `priority='error'` collapse to
`severity='critical'` and we do not attempt to reconstruct the
original tier on downgrade.

---

## 7. `metadata` / `payload` rename

> **Constraint #4.** The Python attribute `payload` MUST remain a
> working **read & write synonym** of `metadata` until Phase 4. Removing
> it before Phase 2 (service-layer migration) would silently break
> in-flight workers that still call `.payload =` /
> `.payload[...] = ...`. The synonym lives on the ORM model for at
> least two release cycles, regardless of how clean Phase 2 looks.

Both `activities.metadata` and `notifications.metadata` are column
renames of the existing `payload` JSON columns. PostgreSQL renames
atomically via `ALTER TABLE … RENAME COLUMN payload TO metadata`, so
existing values are preserved verbatim.

Two follow-ups (both in scope of this revision):

1. **ORM read/write synonym.** The new model declares
   `metadata = mapped_column(...)` as the canonical attribute and
   `payload = synonym("metadata")` as the legacy alias. Both forms
   work, both for ORM-level reads (``obj.payload``) and for SQL-level
   filters (``Activity.payload['k'].astext`` is rewritten to
   ``metadata->>'k'``). The synonym is removed in **Phase 4 cleanup
   only**, never sooner.
2. **Forward-compat producer change.** `notifications.metadata` will
   start carrying the new `title` / `body` keys for forward-compat
   *before* this migration runs (Phase 0 spec change, Phase 1.5
   producer PRs). The migration then pulls those keys back out into
   the canonical columns.

The synonym strategy applies to all renamed columns, not just `payload`.
See §9 for the full list.

---

## 8. Rollback strategy (`downgrade()`)

The migration is **fully reversible** for at least two release cycles.

```sql
-- Phase 1.3 downgrade — reverse of upgrade

-- Drop new indexes / new columns first
DROP INDEX IF EXISTS ix_notifications_tenant_related_entity;
DROP INDEX IF EXISTS ix_notifications_tenant_activity;
DROP INDEX IF EXISTS ix_notifications_tenant_severity_unread;

ALTER TABLE notifications DROP COLUMN IF EXISTS activity_id;
ALTER TABLE notifications DROP COLUMN IF EXISTS severity;
ALTER TABLE notifications DROP COLUMN IF EXISTS body;
ALTER TABLE notifications DROP COLUMN IF EXISTS title;

ALTER INDEX ix_notifications_severity_legacy RENAME TO ix_user_notifications_priority;
ALTER INDEX ix_notifications_type            RENAME TO ix_user_notifications_event_type;
ALTER INDEX ix_notifications_user_id         RENAME TO ix_user_notifications_user_id;
ALTER INDEX ix_notifications_tenant_id       RENAME TO ix_user_notifications_tenant_id;

ALTER TABLE notifications  RENAME COLUMN metadata           TO payload;
ALTER TABLE notifications  RENAME COLUMN related_entity_id  TO entity_id;
ALTER TABLE notifications  RENAME COLUMN related_entity_type TO entity_type;
ALTER TABLE notifications  RENAME COLUMN type               TO event_type;
ALTER TABLE notifications  RENAME TO user_notifications;

DROP INDEX IF EXISTS ix_activities_tenant_starts;
DROP INDEX IF EXISTS ix_activities_tenant_sla;
DROP INDEX IF EXISTS ix_activities_tenant_source;
DROP INDEX IF EXISTS ix_activities_tenant_company;

ALTER TABLE activities DROP COLUMN IF EXISTS sla_status;
ALTER TABLE activities DROP COLUMN IF EXISTS sla_due_at;
ALTER TABLE activities DROP COLUMN IF EXISTS starts_at;
ALTER TABLE activities DROP COLUMN IF EXISTS source_module;
ALTER TABLE activities DROP COLUMN IF EXISTS company_id;

ALTER INDEX ix_activity_events_activity   RENAME TO ix_reminder_events_reminder;
ALTER INDEX ix_activity_events_tenant     RENAME TO ix_reminder_events_tenant;
ALTER INDEX ix_activities_status_due      RENAME TO ix_reminders_status_due;
ALTER INDEX ix_activities_assignee_due    RENAME TO ix_reminders_assignee_due;
ALTER INDEX ix_activities_assignee_reminder RENAME TO ix_reminders_assignee_remind;
ALTER INDEX ix_activities_related_entity  RENAME TO ix_reminders_entity;
ALTER INDEX ix_activities_tenant_due      RENAME TO ix_reminders_tenant_due;

ALTER TABLE activities RENAME COLUMN metadata             TO payload;
ALTER TABLE activities RENAME COLUMN reminder_at          TO remind_at;
ALTER TABLE activities RENAME COLUMN created_by_user_id   TO created_by;
ALTER TABLE activities RENAME COLUMN assigned_to_user_id  TO assignee_id;
ALTER TABLE activities RENAME COLUMN related_entity_id    TO entity_id;
ALTER TABLE activities RENAME COLUMN related_entity_type  TO entity_type;

ALTER TABLE activity_events RENAME COLUMN activity_id TO reminder_id;

ALTER TABLE activity_events RENAME TO reminder_events;
ALTER TABLE activities      RENAME TO reminders;

DROP VIEW IF EXISTS user_notifications;
DROP VIEW IF EXISTS reminders;

-- Status backfill from §3 is one-way and is NOT undone — values 'planned'
-- in the new schema collapse back into the legacy 'pending' bucket on
-- downgrade. The migration logs this caveat in `alembic_version_log`.
UPDATE reminders SET status = 'pending' WHERE status = 'planned';
```

Caveats:

- The `severity`/`title`/`body` data we computed on upgrade is **lost**
  on downgrade. We accept this because the source data still lives in
  `payload` (now back to legacy name). The service layer can recompute
  on the next upgrade attempt.
- The `in_progress` status — if it was assigned by user action between
  the upgrade and the downgrade — must be **manually mapped** to a
  legacy value. The downgrade SQL collapses it to `pending` and writes
  one row per affected `activities.id` to a one-off audit table:
  ```sql
  CREATE TABLE IF NOT EXISTS activity_layer_v1_downgrade_audit (
      activity_id varchar(36) PRIMARY KEY,
      original_status varchar(32) NOT NULL,
      downgraded_at timestamptz NOT NULL DEFAULT now()
  );
  INSERT INTO activity_layer_v1_downgrade_audit (activity_id, original_status)
       SELECT id, status FROM reminders WHERE status NOT IN
           ('new','pending','sent','overdue','done','cancelled')
  ON CONFLICT DO NOTHING;
  UPDATE reminders SET status = 'pending'
   WHERE status NOT IN ('new','pending','sent','overdue','done','cancelled');
  ```

---

## 9. Python model + alias changes during 1.3

In Phase 1.1/1.2 we made `Activity = Reminder`, `Notification =
UserNotification`. After 1.3 the **inversion** happens:

1. `models/activity.py` becomes the **source of truth** with
   `__tablename__ = "activities"`, the canonical column names, and the
   new columns mapped.
2. `models/reminder.py` becomes a **stub** that re-exports
   `Activity as Reminder`. The class identity is preserved
   (`Reminder is Activity`), so existing code that does
   `from backend.app.models import Reminder` continues to work and
   touches the same mapper.
3. Same for `models/reminder_event.py` → `ActivityEvent`.
4. `models/user_notification.py` → `Notification`.
5. `models/__init__.py` keeps both names exported in `__all__` until
   Phase 4 cleanup.

### 9.0 Note on `metadata` attribute naming

The DB column is `metadata` (canonical). On the Python side, that name
is **reserved** by SQLAlchemy Declarative (`Base.metadata` is the
`MetaData` registry). The model attribute is therefore named
`metadata_` and the column name is set explicitly:

```python
metadata_: Mapped[Optional[dict]] = mapped_column(
    "metadata",  # DB column name
    JSON, nullable=True,
)
payload = synonym("metadata_")  # legacy alias — Constraint #4
```

Service code reads/writes `activity.metadata_` for the canonical
attribute, or `activity.payload` for legacy compatibility. SQL
queries reference `Activity.metadata_["k"].astext == "..."` which
is rewritten to `metadata->>'k' = '...'`.

This is the only column where the Python attribute differs from the
DB column name. All other renames keep Python attribute name = DB
column name.

### 9.1 Legacy attribute synonyms (Constraint #4 — kept until Phase 4)

Every renamed column gets a SQLAlchemy `synonym(...)` so legacy code
that reads or writes the old attribute name continues to work — both
in Python (``obj.payload[k] = v``) and in queries
(``Reminder.entity_type == 'lead'`` is rewritten to
``activities.related_entity_type = 'lead'``).

| Legacy attribute | Canonical attribute | Notes |
|---|---|---|
| `Reminder.entity_type`     | `Activity.related_entity_type`    | full read & write |
| `Reminder.entity_id`       | `Activity.related_entity_id`      | full read & write |
| `Reminder.assignee_id`     | `Activity.assigned_to_user_id`    | full read & write |
| `Reminder.created_by`      | `Activity.created_by_user_id`     | full read & write |
| `Reminder.remind_at`       | `Activity.reminder_at`            | full read & write |
| `Reminder.payload`         | `Activity.metadata`               | full read & write — Constraint #4 |
| `ReminderEvent.reminder_id` | `ActivityEvent.activity_id`     | full read & write |
| `UserNotification.event_type`     | `Notification.type`         | full read & write |
| `UserNotification.entity_type`    | `Notification.related_entity_type` | full read & write |
| `UserNotification.entity_id`      | `Notification.related_entity_id`   | full read & write |
| `UserNotification.payload`        | `Notification.metadata`     | full read & write — Constraint #4 |

These synonyms are **mandatory** for Phase 1.3 and **stay until Phase 4
cleanup**, regardless of how clean Phase 2 looks. Removing them earlier
would silently break in-flight workers between rolling-restart waves.

### 9.2 PR boundary

The aliases inversion happens in the **same PR** as the migration so the
code and the schema move atomically. The PR also adds a smoke check at
import time that verifies `Reminder is Activity`,
`ReminderEvent is ActivityEvent`, `UserNotification is Notification`,
and that the synonyms in §9.1 resolve correctly (so a missing synonym
fails fast in CI rather than at runtime in prod).

---

## 10. Linking legacy notifications to activities (`activity_id`)

> **Constraint #3.** Linkage is **high-confidence only**. We do not
> guess. A wrong `activity_id` quietly mis-links a user's notification
> to someone else's task — far worse than leaving it NULL. The Phase
> 1.3 acceptance target is **≥ 50 %** of legacy rows linked; the
> ≥ 80 % target is deferred to Phase 2/3, where producers start
> writing `activity_id` at creation time.

### 10.1 Source 1 — explicit FK in the payload (highest confidence)

If the notification's metadata already carries `activity_id` or
`reminder_id`, use it. This covers any producer that already had the
foresight to record the FK.

```sql
UPDATE notifications n
   SET activity_id = a.id
  FROM activities a
 WHERE n.activity_id IS NULL
   AND a.tenant_id = n.tenant_id
   AND a.id = COALESCE(
       n.metadata->>'activity_id',
       n.metadata->>'reminder_id'
   )
   AND COALESCE(n.metadata->>'activity_id', n.metadata->>'reminder_id') IS NOT NULL;
```

### 10.2 Source 2 — strict tuple match within 5 minutes

For notifications that are clearly the "delivery half" of an activity
creation (e.g. `Activity { type=meeting }` and `Notification {
type=meeting_scheduled }` written in the same transaction), a 5-minute
window with a strict type-pair allow-list is high-confidence enough.

We maintain an **explicit allow-list** of compatible `(activity.type,
notification.type)` pairs — there is no wildcard or LIKE match. The
allow-list lives in the migration as a CTE so it is reviewable in code:

```sql
WITH type_pairs(activity_type, notification_type) AS (
    VALUES
        ('reminder',         'reminder_due'),
        ('reminder',         'reminder_overdue'),
        ('document_check',   'document_expiring'),
        ('document_check',   'document_expired'),
        ('uos_candidate_call',     'candidate_due'),
        ('uos_invoice_follow_payment', 'invoice_due'),
        ('uos_inbound_reply',  'communication_inbound'),
        ('sla_check',          'sla_warning'),
        ('sla_check',          'sla_breached')
)
UPDATE notifications n
   SET activity_id = a.id
  FROM activities a, type_pairs tp
 WHERE n.activity_id IS NULL
   AND a.tenant_id            = n.tenant_id
   AND a.related_entity_type  = n.related_entity_type
   AND a.related_entity_id    = n.related_entity_id
   AND a.related_entity_type IS NOT NULL
   AND a.related_entity_id   IS NOT NULL
   AND a.type                 = tp.activity_type
   AND n.type                 = tp.notification_type
   AND a.created_at <= n.created_at
   AND a.created_at >  n.created_at - INTERVAL '5 minutes';
```

If multiple activities match the strict tuple, **none** is picked — we
prefer NULL over an arbitrary tie-break. Operationally we do this by
adding a `NOT EXISTS (… COUNT(*) > 1 …)` guard:

```sql
-- (the production migration wraps the UPDATE above in a CTE that
-- excludes any (n.id) for which more than one activity matches)
```

### 10.3 What we do NOT attempt

The following heuristics are explicitly **rejected** for Phase 1.3 (and
will only be revisited if/when telemetry shows a strong signal):

- 24-hour or longer window matching ❌
- "most recent activity on the same entity" ❌
- Text/title fuzzy match between notification and activity ❌
- `assignee_id == user_id` proximity matching ❌
- Stage-history correlation ❌

### 10.4 Acceptance

§11 reports `notifications_activity_id_linked_pct` overall plus
per-source (1 = payload FK, 2 = strict tuple, 0 = unlinked). Phase 1.3
acceptance is **≥ 50 %**. The remaining gap is closed in Phase 2/3 by:

- adding `activity_id` to every producer at creation time (Phase 2);
- back-filling on the next read when the user opens the bell
  (Phase 3 — opportunistic linker that runs the §10.1/§10.2 logic
  per-notification with stricter tenant-locality guarantees).

---

## 11. Observability & success criteria

The migration emits the following counters into Datadog (or stdout, on
staging) before, after upgrade, after backfill, and after downgrade:

| Metric | What we read |
|---|---|
| `activities_total`                      | `SELECT COUNT(*) FROM activities`        |
| `activities_company_id_null`            | rows with NULL company_id after backfill |
| `activities_status_legacy`              | rows still in `new`/`pending`/`sent`     |
| `activities_source_module_unknown`      | rows with `source_module = 'unknown'`    |
| `notifications_total`                   | `SELECT COUNT(*) FROM notifications`     |
| `notifications_severity_null`           | rows with NULL severity after backfill   |
| `notifications_activity_id_linked_pct`  | `activity_id` filled / total             |
| `notifications_title_null`              | NULL title (should be 0 after backfill)  |

**Acceptance criteria:**

Hard gates (migration aborts if violated):

- `activities_status_legacy = 0` (UPDATE in §3 is deterministic).
- `notifications_severity_null = 0` (UPDATE in §6.3 is deterministic).
- `notifications_title_null = 0` (UPDATE in §6.1 is deterministic).

Soft gates (observability targets — investigate but do not abort, since
constraint #2 prefers NULL over a wrong value):

- `activities_company_id_null / activities_total` is **observed** and
  reported per source (1 = metadata, 2 = direct company, 3 = entity FK,
  4 = unique tenant company). No fixed threshold — the canary report is
  reviewed by hand. If a tenant has > 50 % NULL after backfill, the
  per-source histogram tells us whether it's missing source 4 (multi-
  company tenant, expected) or missing source 3 (data quality issue,
  needs investigation).
- `activities_source_module_unknown / activities_total ≤ 1 %` (else
  add a missing branch in §5 and re-run).
- `notifications_activity_id_linked_pct ≥ 50 %` on tenants with at
  least 100 activities and 100 notifications. The ≥ 80 % target is
  **deferred** to Phase 2/3 (constraint #3) — high-confidence-only
  linkage is the rule for 1.3, even when it costs coverage.

---

## 12. Staging canary plan

1. **Snapshot:** clone latest staging Postgres into a fresh DB
   (`hostflow_staging_p13_canary`).
2. **Pre-flight:** run §11 metrics against the snapshot, archive output.
3. **Apply:** run `alembic upgrade activity_layer_v1` against the canary DB.
4. **Re-measure:** run §11 metrics against the upgraded DB, diff
   against pre-flight.
5. **Smoke tests** (write-path):
   - Create a new activity via the legacy `/api/v1/reminders` endpoint
     → row appears in `activities`, `source_module` populated, `company_id`
     populated when the linked entity provides one.
   - Create a notification via the legacy `/api/v1/notifications`
     endpoint → row appears in `notifications` with `severity`, `title`,
     `body` populated by the producer (we expect Phase 1.5 producer
     changes to land **before** 1.3, see §13).
   - Mark a notification as read → row in `notifications` flips
     `is_read=true`, `read_at` set.
6. **Smoke tests** (read-path):
   - `/api/v1/reminders` GET still works (compat layer reads from
     `activities` via the renamed columns).
   - `/api/v1/notifications` GET returns rows with `severity` filled.
   - bell counter on the topbar shows the same unread count as before
     migration.
7. **Rollback drill:** run `alembic downgrade -1` on the canary; verify
   `reminders` / `user_notifications` reappear, row counts match
   pre-flight, the audit table from §8 is populated for any rows whose
   status had moved to `in_progress` during the canary.
8. **Promote:** if all checks pass, schedule the prod migration in a
   maintenance window with the same script.

---

## 13. Producer changes that must land **before** 1.3

These are pre-conditions; they ship in their own PR ahead of 1.3 and
must be running in prod for at least one release before 1.3 is applied:

- All notification producers must write `payload['title']`,
  `payload['body']`, `payload['severity']`. (Already partly done for
  document expiry and SLA; remaining producers tracked in
  `docs/specs/workflows/activities-sla-matrix.md` §3.)
- All reminder producers must write `payload['source_module']` and
  `payload['company_id']` when known. (Backfill in §4/§5 handles the
  history; producers handle the present.)
- Worker daemons must be restarted on the new container image so they
  start reading the `metadata` column transparently (the model adds
  the `synonym` so this is a no-op for code, but the container must
  pick up the new SQLAlchemy class).

If any of these is **not** in prod, Phase 1.3 stops at staging.

---

## 14. Out-of-scope for 1.3 (intentional)

- **Dropping legacy columns** (`assignee_id`, `created_by`, `priority`,
  `event_type`, `entity_type`, `entity_id` etc. left as **synonyms** of
  the canonical columns). They go away in **Phase 4 cleanup**, in their
  own ADR-012 follow-up revision, after Phase 2 (HTTP API) and Phase 3
  (frontend) confirm no consumer reads the legacy names anymore.
- **CHECK constraints** on `status`, `severity`, `source_module`. They
  land in Phase 4 once telemetry confirms no producer writes off-grid
  values.
- **NOT NULL** on `company_id`, `severity`, `title`. Phase 4 only.
- **Compatibility view drop** (§2.3). Phase 4.
- **Calendar consolidation** (`calendar_items` ↔ `activities` of type
  meeting/call). That's its own migration, gated separately, after
  Phase 2.
- **`automation_rules` evolution** to drive Activity creation from
  events. Phase 1.5 / Phase 2 — not part of 1.3.

---

## 15. Approval checklist & deploy mechanics

### 15.1 Deploy mechanics

Phase 1.3 ships the migration **and** the model rewire (§9) in **one
PR**, deployed atomically:

1. Code with the new ORM (`__tablename__ = "activities"`, etc.) is
   built and pushed to the deploy artifact registry.
2. In a **maintenance window** (≤ 5 min for the largest tenant):
   - the prod DB is backed up;
   - `alembic upgrade activity_layer_v1` is run by the migration job;
   - the new code is rolled out to web + worker fleets.
3. A **startup-check** in app boot verifies that the canonical tables
   exist (`activities`, `notifications`, `activity_events`). If any is
   missing, the container exits with a clear error before serving
   traffic. This catches the "code rolled out but migration didn't
   apply" failure mode loudly instead of silently 500-ing every query.

There is **no feature flag**. A feature flag for a schema rename is a
trap: half the fleet runs against the old schema and half against the
new, with no clean way to read both. Maintenance window + startup-check
is the cleaner pattern for irreversible-by-default DDL.

If we later need to roll back:

- `git revert` the PR (returns ORM to legacy names).
- `alembic downgrade -1` (returns DB to legacy schema).
- Both must happen together; the §8 audit table captures any
  `in_progress` row that lived during the upgraded window.

### 15.2 Approval gate

Before this revision is merged, the following must be ✅:

- [ ] §13 producer changes are deployed to prod ≥ 1 release ago.
- [ ] §12 staging canary has run cleanly with all §11 hard gates green
      and soft gates within the documented expectations.
- [ ] §8 rollback drill has been executed end-to-end on the canary
      (upgrade → in_progress mutation → downgrade → assert audit).
- [ ] §9 ORM smoke tests are green: every legacy attribute synonym
      resolves to the canonical column (read **and** write paths).
- [ ] Maintenance window is scheduled.
- [ ] On-call has the rollback runbook linked from this doc.
- [ ] Phase 2 (HTTP API consolidation) PR is queued and ready to
      deploy in the next release window — we do not want to run for
      long with `synonym`-only legacy support.

When all seven are ✅, this doc is moved from `ACCEPTED (with
constraints)` to `MERGED`, and the migration goes out in the next
maintenance window.
