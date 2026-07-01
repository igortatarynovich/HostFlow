"""planner_tasks_into_activities — Phase 2.1 backfill (ADR-012).

Revision ID: 202607150004_pti
Revises: 202607150003_cvla
Create Date: 2026-05-09

Phase 2.1 of the Activity & Notification Operating Layer rollout.

Backfills two legacy operational-task tables into the canonical ``activities``
table so the duplicate task surfaces (`/api/v1/candidates/{id}/tasks`,
`/api/v1/communications/planner/events*`) can be removed in a follow-up
revision (`202607150005_drop_planner_tasks_tables`):

* ``candidate_tasks``               → ``activities`` (`type='task'`,
                                       `source_module='candidates'`).
* ``communication_planner_events``  → ``activities`` with canonical
                                       ``type ∈ {task, follow_up, call,
                                       meeting, custom}`` and
                                       `source_module='comms'`.

Mapping rules, fallbacks, metadata shape and acceptance criteria are
documented in
``docs/specs/architecture/phase-2-1-planner-tasks-into-activities.md``
(plan accepted 2026-05-09).

Six binding decisions enforced by this migration:

1. Canonical ``type`` set is `task | follow_up | call | meeting | custom`.
   We do **not** introduce ``planner_*`` types — origin lives in
   ``source_module`` + ``metadata.legacy_source``.
2. Legacy provenance is recorded **only** in
   ``metadata.legacy_source`` (`candidate_tasks` /
   ``communication_planner_events``). ``downgrade()`` deletes by this
   key, never by ``type``.
3. ``candidate_tasks.due_on`` fallback for ``NULL`` is ``due_at =
   updated_at`` + ``metadata.legacy.due_synthesized=true``,
   ``due_reason='missing_due_on'``. We never fabricate a deadline.
4. ``communication_planner_events`` rows with neither ``entity_type/id``
   nor ``linked_candidate_id`` get ``related_entity_type =
   'planner_event_legacy'``, ``related_entity_id = pe.id`` and
   ``metadata.legacy.unresolved_related_entity=true`` — explicit
   "no real entity" marker, not a faked ``custom`` link.
5. ``unparseable_due_on`` does **not** fail the migration. We capture
   the raw value in ``metadata.legacy.due_on_raw`` and report counts in
   the audit row. Acceptance is ``rows_inserted == legacy_total`` only.
6. The legacy tables are **kept in place**. Drop is a separate revision
   (`202607150005_drop_planner_tasks_tables`) gated on canary.

Idempotency: ``WHERE NOT EXISTS (SELECT 1 FROM activities WHERE id = ...)``
on every INSERT, so re-running ``alembic upgrade head`` is safe.

Dialect note: production is PostgreSQL — the fast path uses
``jsonb_build_object`` / ``regex`` / ``CASE``. SQLite is supported for
``round-trip`` tests via a Python-loop fallback that uses ``json``,
``re`` and ``INSERT OR IGNORE``.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607150004_pti"
down_revision: Union[str, None] = "202607150003_cvla"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


logger = logging.getLogger("alembic.runtime.migration")

_AUDIT_TABLE = "phase_2_1_backfill_audit"
_UUID_REGEX = (
    "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    "[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_UUID_RE_PY = re.compile(_UUID_REGEX)
_ISO_DATE_RE_PY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Helpers (inspector + dialect probe).
# ---------------------------------------------------------------------------


def _is_postgres(conn: sa.Connection) -> bool:
    return conn.dialect.name == "postgresql"


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in set(sa.inspect(conn).get_table_names())


# ---------------------------------------------------------------------------
# Audit table — one row per ``upgrade()`` invocation with backfill counts.
# Lives across ``downgrade()`` so re-running upgrade can compare runs.
# ---------------------------------------------------------------------------


def _ensure_audit_table(conn: sa.Connection) -> None:
    if _has_table(conn, _AUDIT_TABLE):
        return
    op.create_table(
        _AUDIT_TABLE,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
    )


def _write_audit(conn: sa.Connection, *, kind: str, payload: dict[str, Any]) -> None:
    _ensure_audit_table(conn)
    # Cast the bound JSON payload explicitly so PostgreSQL accepts it
    # (the audit column is ``JSON``; SQLAlchemy passes string parameters
    # as ``VARCHAR`` by default, which PG rejects). SQLite ignores the
    # cast — its JSON column is just TEXT.
    if _is_postgres(conn):
        sql = (
            f"INSERT INTO {_AUDIT_TABLE} (kind, payload) "
            "VALUES (:kind, CAST(:payload AS json))"
        )
    else:
        sql = (
            f"INSERT INTO {_AUDIT_TABLE} (kind, payload) VALUES (:kind, :payload)"
        )
    conn.execute(
        sa.text(sql),
        {"kind": kind, "payload": json.dumps(payload, default=str)},
    )


# ---------------------------------------------------------------------------
# PG fast path — INSERT ... SELECT with CASE expressions.
# ---------------------------------------------------------------------------


_PG_INSERT_CANDIDATE_TASKS = f"""
INSERT INTO activities (
    id, tenant_id,
    type, source_module, source,
    related_entity_type, related_entity_id,
    company_id,
    title, description,
    status, priority,
    starts_at, due_at, reminder_at, duration_minutes,
    assigned_to_user_id, created_by_user_id, owner_id,
    metadata,
    completed_at, cancelled_at,
    created_at, updated_at
)
SELECT
    ct.id,
    ct.tenant_id,

    'task',
    'candidates',
    'candidate_task_legacy',

    'candidate',
    ct.candidate_id,
    NULL,                                           -- company_id (no-guess)

    ct.title,
    ct.description,

    CASE
      WHEN ct.completed = 1                                          THEN 'done'
      WHEN LOWER(COALESCE(ct.status,'')) IN ('completed','done')      THEN 'done'
      WHEN LOWER(COALESCE(ct.status,'')) IN ('cancelled','canceled')  THEN 'cancelled'
      WHEN LOWER(COALESCE(ct.status,'')) = 'in_progress'              THEN 'in_progress'
      ELSE 'planned'
    END,
    NULLIF(ct.priority,''),

    NULL,                                           -- starts_at
    CASE
      WHEN ct.due_on ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}$'
        THEN ((ct.due_on || ' 23:59:59+00')::timestamptz)
      ELSE ct.updated_at
    END,
    NULL,                                           -- reminder_at
    NULL,                                           -- duration_minutes

    CASE
      WHEN ct.assigned_to ~ '{_UUID_REGEX}'
       AND EXISTS (
         SELECT 1 FROM users u
          WHERE u.id = ct.assigned_to
            AND u.tenant_id = ct.tenant_id
       )
      THEN ct.assigned_to
      ELSE NULL
    END,
    NULL,                                           -- created_by_user_id
    NULL,                                           -- owner_id

    (
      jsonb_build_object(
        'legacy_source', 'candidate_tasks',
        'legacy', (
          '{{}}'::jsonb
          || CASE
               WHEN ct.assigned_to IS NOT NULL
                    AND NOT (ct.assigned_to ~ '{_UUID_REGEX}')
               THEN jsonb_build_object('assigned_to_raw', ct.assigned_to)
               ELSE '{{}}'::jsonb
             END
          || CASE
               WHEN ct.due_on IS NULL
               THEN jsonb_build_object(
                      'due_synthesized', true,
                      'due_reason',      'missing_due_on'
                    )
               WHEN NOT (ct.due_on ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}$')
               THEN jsonb_build_object(
                      'due_synthesized', true,
                      'due_reason',      'unparseable_due_on',
                      'due_on_raw',      ct.due_on
                    )
               ELSE '{{}}'::jsonb
             END
          || CASE
               WHEN ct.meta IS NOT NULL AND ct.meta NOT IN ('','{{}}')
               THEN jsonb_build_object('candidate_task_meta_raw', ct.meta)
               ELSE '{{}}'::jsonb
             END
        )
      )
    )::json,

    CASE
      WHEN ct.completed = 1
        OR LOWER(COALESCE(ct.status,'')) IN ('completed','done')
      THEN ct.updated_at
      ELSE NULL
    END,
    NULL,                                           -- cancelled_at

    ct.created_at,
    ct.updated_at
FROM candidate_tasks ct
WHERE NOT EXISTS (SELECT 1 FROM activities a WHERE a.id = ct.id);
"""


_PG_INSERT_PLANNER_EVENTS = f"""
INSERT INTO activities (
    id, tenant_id,
    type, source_module, source,
    related_entity_type, related_entity_id,
    company_id,
    title, description,
    status, priority,
    starts_at, due_at, reminder_at, duration_minutes,
    assigned_to_user_id, created_by_user_id, owner_id,
    metadata,
    completed_at, cancelled_at,
    created_at, updated_at
)
SELECT
    pe.id,
    pe.tenant_id,

    CASE LOWER(COALESCE(pe.kind,'task'))
      WHEN 'task'     THEN 'task'
      WHEN 'followup' THEN 'follow_up'
      WHEN 'call'     THEN 'call'
      WHEN 'meeting'  THEN 'meeting'
      WHEN 'shift'    THEN 'custom'
      ELSE 'custom'
    END,
    'comms',
    pe.source,

    CASE
      WHEN COALESCE(pe.entity_type,'') <> '' AND COALESCE(pe.entity_id,'') <> ''
        THEN pe.entity_type
      WHEN pe.linked_candidate_id IS NOT NULL
        THEN 'candidate'
      ELSE 'planner_event_legacy'
    END,
    CASE
      WHEN COALESCE(pe.entity_type,'') <> '' AND COALESCE(pe.entity_id,'') <> ''
        THEN pe.entity_id
      WHEN pe.linked_candidate_id IS NOT NULL
        THEN pe.linked_candidate_id
      ELSE pe.id
    END,

    -- company_id: no-guess. Sources are explicit linked_company_id,
    -- explicit payload key, or related_entity_type='company'.
    CASE
      WHEN pe.linked_company_id ~ '{_UUID_REGEX}'
        THEN pe.linked_company_id
      WHEN (pe.payload::jsonb ->> 'company_id') ~ '{_UUID_REGEX}'
        THEN (pe.payload::jsonb ->> 'company_id')
      WHEN COALESCE(pe.entity_type,'') = 'company'
       AND pe.entity_id ~ '{_UUID_REGEX}'
        THEN pe.entity_id
      ELSE NULL
    END,

    pe.title,
    pe.description,

    CASE LOWER(COALESCE(pe.status,'planned'))
      WHEN 'planned'     THEN 'planned'
      WHEN 'in_progress' THEN 'in_progress'
      WHEN 'done'        THEN 'done'
      WHEN 'cancelled'   THEN 'cancelled'
      ELSE 'planned'
    END,
    NULLIF(pe.priority,''),

    -- starts_at: only for time-bound kinds (task/followup are deadlines).
    CASE LOWER(COALESCE(pe.kind,'task'))
      WHEN 'task'     THEN NULL
      WHEN 'followup' THEN NULL
      ELSE pe.start_at
    END,
    -- due_at: pe.start_at is NOT NULL upstream, so no NULL fallback needed.
    COALESCE(pe.end_at, pe.start_at),
    NULL,
    CASE
      WHEN pe.start_at IS NOT NULL AND pe.end_at IS NOT NULL
      THEN GREATEST(0, EXTRACT(EPOCH FROM (pe.end_at - pe.start_at))/60)::int
      ELSE NULL
    END,

    pe.assignee_id,
    NULL,
    pe.owner_id,

    -- metadata = pe.payload (preserved) merged with our keys (overwriting on clash).
    (
      COALESCE(pe.payload::jsonb, '{{}}'::jsonb)
      || jsonb_build_object(
           'legacy_source', 'communication_planner_events',
           'planner', (
             jsonb_build_object(
               'kind',       pe.kind,
               'all_day',    pe.all_day,
               'source_raw', pe.source
             )
             || CASE
                  WHEN pe.linked_candidate_id IS NOT NULL
                       AND NOT (
                         COALESCE(pe.entity_type,'') = 'candidate'
                         AND pe.entity_id = pe.linked_candidate_id
                       )
                  THEN jsonb_build_object('linked_candidate_id', pe.linked_candidate_id)
                  ELSE '{{}}'::jsonb
                END
             || CASE
                  WHEN pe.linked_company_id IS NOT NULL
                       AND NOT (pe.linked_company_id ~ '{_UUID_REGEX}')
                  THEN jsonb_build_object('linked_company_id', pe.linked_company_id)
                  ELSE '{{}}'::jsonb
                END
           ),
           'legacy', (
             '{{}}'::jsonb
             || CASE
                  WHEN COALESCE(pe.entity_type,'') = ''
                       AND pe.linked_candidate_id IS NULL
                  THEN jsonb_build_object('unresolved_related_entity', true)
                  ELSE '{{}}'::jsonb
                END
             || CASE
                  WHEN LOWER(COALESCE(pe.status,'planned'))
                       NOT IN ('planned','in_progress','done','cancelled')
                  THEN jsonb_build_object('status_raw', pe.status)
                  ELSE '{{}}'::jsonb
                END
           )
         )
    )::json,

    CASE WHEN LOWER(COALESCE(pe.status,'')) = 'done'
         THEN pe.updated_at ELSE NULL END,
    CASE WHEN LOWER(COALESCE(pe.status,'')) = 'cancelled'
         THEN pe.updated_at ELSE NULL END,

    pe.created_at,
    pe.updated_at
FROM communication_planner_events pe
WHERE NOT EXISTS (SELECT 1 FROM activities a WHERE a.id = pe.id);
"""


# ---------------------------------------------------------------------------
# SQLite fallback — Python-side projection for the round-trip test path.
#
# Same mapping rules as the PG SQL above, expressed in Python because
# SQLite has no jsonb / regex operators / interval arithmetic in core.
# Idempotency: relies on PRIMARY KEY conflicts being silently skipped
# via ``INSERT OR IGNORE``.
# ---------------------------------------------------------------------------


def _parse_due_on(due_on: str | None) -> tuple[str | None, str | None, str | None]:
    """Returns (due_iso, due_reason, due_on_raw)."""
    if due_on is None:
        return None, "missing_due_on", None
    raw = str(due_on).strip()
    if not raw:
        return None, "missing_due_on", None
    if not _ISO_DATE_RE_PY.match(raw):
        return None, "unparseable_due_on", raw
    return f"{raw} 23:59:59+00:00", None, None


def _looks_like_uuid(value: Any) -> bool:
    if value is None:
        return False
    return bool(_UUID_RE_PY.match(str(value)))


_PLANNER_TYPE_MAP = {
    "task": "task",
    "followup": "follow_up",
    "call": "call",
    "meeting": "meeting",
    "shift": "custom",
}

_PLANNER_STATUS_MAP = {
    "planned": "planned",
    "in_progress": "in_progress",
    "done": "done",
    "cancelled": "cancelled",
}


def _ct_status(row: sa.engine.Row) -> tuple[str, datetime | None]:
    """Returns (status, completed_at)."""
    completed_flag = int(row.completed or 0) == 1
    raw = (row.status or "").strip().lower()
    if completed_flag or raw in ("completed", "done"):
        return "done", row.updated_at
    if raw in ("cancelled", "canceled"):
        return "cancelled", None
    if raw == "in_progress":
        return "in_progress", None
    return "planned", None


def _backfill_candidate_tasks_sqlite(conn: sa.Connection) -> dict[str, int]:
    if not _has_table(conn, "candidate_tasks"):
        return {"inserted": 0, "skipped": 0, "missing_due_on": 0, "unparseable_due_on": 0}
    rows = conn.execute(sa.text(
        "SELECT id, tenant_id, candidate_id, title, description, status, "
        "       due_on, priority, assigned_to, completed, meta, "
        "       created_at, updated_at "
        "  FROM candidate_tasks"
    )).all()

    user_lookup_stmt = sa.text(
        "SELECT 1 FROM users WHERE id = :uid AND tenant_id = :tid LIMIT 1"
    )

    inserted = 0
    skipped = 0
    missing_due_on = 0
    unparseable_due_on = 0
    insert_stmt = sa.text(
        "INSERT OR IGNORE INTO activities ("
        "  id, tenant_id, type, source_module, source,"
        "  related_entity_type, related_entity_id, company_id,"
        "  title, description, status, priority,"
        "  starts_at, due_at, reminder_at, duration_minutes,"
        "  assigned_to_user_id, created_by_user_id, owner_id,"
        "  metadata, completed_at, cancelled_at, created_at, updated_at"
        ") VALUES ("
        "  :id, :tenant_id, 'task', 'candidates', 'candidate_task_legacy',"
        "  'candidate', :related_entity_id, NULL,"
        "  :title, :description, :status, :priority,"
        "  NULL, :due_at, NULL, NULL,"
        "  :assigned_to_user_id, NULL, NULL,"
        "  :metadata, :completed_at, NULL, :created_at, :updated_at"
        ")"
    )

    for row in rows:
        legacy_chunk: dict[str, Any] = {}

        if row.assigned_to and not _looks_like_uuid(row.assigned_to):
            legacy_chunk["assigned_to_raw"] = row.assigned_to

        due_iso, due_reason, due_raw = _parse_due_on(row.due_on)
        if due_reason == "missing_due_on":
            missing_due_on += 1
            legacy_chunk["due_synthesized"] = True
            legacy_chunk["due_reason"] = "missing_due_on"
        elif due_reason == "unparseable_due_on":
            unparseable_due_on += 1
            legacy_chunk["due_synthesized"] = True
            legacy_chunk["due_reason"] = "unparseable_due_on"
            legacy_chunk["due_on_raw"] = due_raw

        if row.meta and str(row.meta).strip() not in ("", "{}"):
            legacy_chunk["candidate_task_meta_raw"] = row.meta

        metadata = {"legacy_source": "candidate_tasks", "legacy": legacy_chunk}

        if due_iso is None:
            due_at = row.updated_at
        else:
            due_at = due_iso

        assigned_to_user_id: str | None = None
        if row.assigned_to and _looks_like_uuid(row.assigned_to):
            user_hit = conn.execute(
                user_lookup_stmt, {"uid": row.assigned_to, "tid": row.tenant_id}
            ).first()
            if user_hit is not None:
                assigned_to_user_id = row.assigned_to

        status_value, completed_at = _ct_status(row)

        priority = (row.priority or "").strip() or None

        result = conn.execute(
            insert_stmt,
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "related_entity_id": row.candidate_id,
                "title": row.title,
                "description": row.description,
                "status": status_value,
                "priority": priority,
                "due_at": due_at,
                "assigned_to_user_id": assigned_to_user_id,
                "metadata": json.dumps(metadata, default=str),
                "completed_at": completed_at,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            },
        )
        if result.rowcount and result.rowcount > 0:
            inserted += 1
        else:
            skipped += 1

    return {
        "inserted": inserted,
        "skipped": skipped,
        "missing_due_on": missing_due_on,
        "unparseable_due_on": unparseable_due_on,
    }


def _backfill_planner_events_sqlite(conn: sa.Connection) -> dict[str, int]:
    if not _has_table(conn, "communication_planner_events"):
        return {"inserted": 0, "skipped": 0, "unresolved_related_entities": 0}
    rows = conn.execute(sa.text(
        "SELECT id, tenant_id, title, description, kind, status, priority,"
        "       start_at, end_at, all_day, owner_id, assignee_id,"
        "       entity_type, entity_id, linked_candidate_id, linked_company_id,"
        "       source, payload, created_at, updated_at "
        "  FROM communication_planner_events"
    )).all()

    inserted = 0
    skipped = 0
    unresolved = 0
    insert_stmt = sa.text(
        "INSERT OR IGNORE INTO activities ("
        "  id, tenant_id, type, source_module, source,"
        "  related_entity_type, related_entity_id, company_id,"
        "  title, description, status, priority,"
        "  starts_at, due_at, reminder_at, duration_minutes,"
        "  assigned_to_user_id, created_by_user_id, owner_id,"
        "  metadata, completed_at, cancelled_at, created_at, updated_at"
        ") VALUES ("
        "  :id, :tenant_id, :type, 'comms', :source,"
        "  :related_entity_type, :related_entity_id, :company_id,"
        "  :title, :description, :status, :priority,"
        "  :starts_at, :due_at, NULL, :duration_minutes,"
        "  :assigned_to_user_id, NULL, :owner_id,"
        "  :metadata, :completed_at, :cancelled_at, :created_at, :updated_at"
        ")"
    )

    for row in rows:
        kind_raw = (row.kind or "task").strip().lower()
        canonical_type = _PLANNER_TYPE_MAP.get(kind_raw, "custom")

        status_raw = (row.status or "planned").strip().lower()
        canonical_status = _PLANNER_STATUS_MAP.get(status_raw, "planned")

        # related_entity fallback
        if (row.entity_type and str(row.entity_type).strip()
                and row.entity_id and str(row.entity_id).strip()):
            related_type = row.entity_type
            related_id = row.entity_id
        elif row.linked_candidate_id:
            related_type = "candidate"
            related_id = row.linked_candidate_id
        else:
            related_type = "planner_event_legacy"
            related_id = row.id
            unresolved += 1

        # company_id no-guess
        company_id: str | None = None
        if row.linked_company_id and _looks_like_uuid(row.linked_company_id):
            company_id = row.linked_company_id
        else:
            payload_obj: dict[str, Any] = {}
            if row.payload:
                try:
                    payload_obj = json.loads(row.payload) if isinstance(row.payload, str) else dict(row.payload)
                except Exception:
                    payload_obj = {}
            cand = payload_obj.get("company_id") if isinstance(payload_obj, dict) else None
            if cand and _looks_like_uuid(cand):
                company_id = str(cand)
            elif (row.entity_type or "") == "company" and _looks_like_uuid(row.entity_id):
                company_id = row.entity_id

        # starts_at — only for time-bound kinds.
        if kind_raw in ("task", "followup"):
            starts_at = None
        else:
            starts_at = row.start_at

        # due_at = COALESCE(end_at, start_at). start_at is NOT NULL upstream.
        due_at = row.end_at or row.start_at

        # duration_minutes
        duration_minutes: int | None = None
        if row.start_at and row.end_at:
            try:
                start_dt = (
                    row.start_at if isinstance(row.start_at, datetime)
                    else datetime.fromisoformat(str(row.start_at).replace("Z", "+00:00"))
                )
                end_dt = (
                    row.end_at if isinstance(row.end_at, datetime)
                    else datetime.fromisoformat(str(row.end_at).replace("Z", "+00:00"))
                )
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                delta = (end_dt - start_dt).total_seconds() / 60
                duration_minutes = max(0, int(delta))
            except Exception:
                duration_minutes = None

        # metadata = pe.payload merged with our keys.
        try:
            payload_obj = json.loads(row.payload) if isinstance(row.payload, str) and row.payload else (
                dict(row.payload) if isinstance(row.payload, dict) else {}
            )
        except Exception:
            payload_obj = {}
        metadata = dict(payload_obj) if isinstance(payload_obj, dict) else {}

        planner_meta: dict[str, Any] = {
            "kind": row.kind,
            "all_day": bool(row.all_day),
            "source_raw": row.source,
        }
        if row.linked_candidate_id and not (
            (row.entity_type or "") == "candidate" and row.entity_id == row.linked_candidate_id
        ):
            planner_meta["linked_candidate_id"] = row.linked_candidate_id
        if row.linked_company_id and not _looks_like_uuid(row.linked_company_id):
            planner_meta["linked_company_id"] = row.linked_company_id

        legacy_meta: dict[str, Any] = {}
        if not (row.entity_type and str(row.entity_type).strip()) and not row.linked_candidate_id:
            legacy_meta["unresolved_related_entity"] = True
        if status_raw not in _PLANNER_STATUS_MAP:
            legacy_meta["status_raw"] = row.status

        metadata["legacy_source"] = "communication_planner_events"
        metadata["planner"] = planner_meta
        if legacy_meta:
            metadata["legacy"] = legacy_meta

        priority = (row.priority or "").strip() or None

        completed_at = row.updated_at if status_raw == "done" else None
        cancelled_at = row.updated_at if status_raw == "cancelled" else None

        result = conn.execute(
            insert_stmt,
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "type": canonical_type,
                "source": row.source,
                "related_entity_type": related_type,
                "related_entity_id": related_id,
                "company_id": company_id,
                "title": row.title,
                "description": row.description,
                "status": canonical_status,
                "priority": priority,
                "starts_at": starts_at,
                "due_at": due_at,
                "duration_minutes": duration_minutes,
                "assigned_to_user_id": row.assignee_id,
                "owner_id": row.owner_id,
                "metadata": json.dumps(metadata, default=str),
                "completed_at": completed_at,
                "cancelled_at": cancelled_at,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            },
        )
        if result.rowcount and result.rowcount > 0:
            inserted += 1
        else:
            skipped += 1

    return {
        "inserted": inserted,
        "skipped": skipped,
        "unresolved_related_entities": unresolved,
    }


# ---------------------------------------------------------------------------
# Counts (PG path) — used by the audit row.
# ---------------------------------------------------------------------------


def _count(conn: sa.Connection, sql: str) -> int:
    try:
        return int((conn.execute(sa.text(sql)).scalar()) or 0)
    except Exception:
        return 0


def _pg_counts(conn: sa.Connection) -> dict[str, int]:
    return {
        "candidate_tasks_total":
            _count(conn, "SELECT count(*) FROM candidate_tasks")
            if _has_table(conn, "candidate_tasks") else 0,
        "planner_events_total":
            _count(conn, "SELECT count(*) FROM communication_planner_events")
            if _has_table(conn, "communication_planner_events") else 0,
        "candidate_tasks_inserted": _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='candidates' "
            "   AND metadata::jsonb ->> 'legacy_source' = 'candidate_tasks'",
        ),
        "planner_events_inserted": _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='comms' "
            "   AND metadata::jsonb ->> 'legacy_source' = 'communication_planner_events'",
        ),
        "missing_due_on": _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='candidates' "
            "   AND metadata::jsonb #>> '{legacy,due_reason}' = 'missing_due_on'",
        ),
        "unparseable_due_on": _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='candidates' "
            "   AND metadata::jsonb #>> '{legacy,due_reason}' = 'unparseable_due_on'",
        ),
        "unresolved_related_entities": _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='comms' "
            "   AND metadata::jsonb #>> '{legacy,unresolved_related_entity}' = 'true'",
        ),
    }


def _sqlite_counts(conn: sa.Connection) -> dict[str, int]:
    return {
        "candidate_tasks_total":
            _count(conn, "SELECT count(*) FROM candidate_tasks")
            if _has_table(conn, "candidate_tasks") else 0,
        "planner_events_total":
            _count(conn, "SELECT count(*) FROM communication_planner_events")
            if _has_table(conn, "communication_planner_events") else 0,
        "candidate_tasks_inserted": _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='candidates' "
            "   AND json_extract(metadata, '$.legacy_source') = 'candidate_tasks'",
        ),
        "planner_events_inserted": _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='comms' "
            "   AND json_extract(metadata, '$.legacy_source') = 'communication_planner_events'",
        ),
        "missing_due_on": _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='candidates' "
            "   AND json_extract(metadata, '$.legacy.due_reason') = 'missing_due_on'",
        ),
        "unparseable_due_on": _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='candidates' "
            "   AND json_extract(metadata, '$.legacy.due_reason') = 'unparseable_due_on'",
        ),
        "unresolved_related_entities": _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='comms' "
            "   AND json_extract(metadata, '$.legacy.unresolved_related_entity') = 1",
        ),
    }


# ---------------------------------------------------------------------------
# Public entry points.
# ---------------------------------------------------------------------------


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "activities"):
        # Phase 1.3 has not been applied yet — Phase 2.1 cannot proceed.
        # Surface loudly so the operator runs ``alembic upgrade`` from the
        # right starting point instead of silently producing no rows.
        raise RuntimeError(
            "Phase 2.1 backfill requires Phase 1.3 (`activities` table) — "
            "run `alembic upgrade 202607150003_cvla` first."
        )

    _ensure_audit_table(conn)

    if _is_postgres(conn):
        if _has_table(conn, "candidate_tasks"):
            op.execute(sa.text(_PG_INSERT_CANDIDATE_TASKS))
        if _has_table(conn, "communication_planner_events"):
            op.execute(sa.text(_PG_INSERT_PLANNER_EVENTS))
        counts = _pg_counts(conn)
    else:
        ct_counts = _backfill_candidate_tasks_sqlite(conn)
        pe_counts = _backfill_planner_events_sqlite(conn)
        # Acceptance counts come from the canonical projection (matching
        # ``metadata.legacy_source``), not the per-row ``inserted``
        # counter — the per-row counter goes to zero on a re-run because
        # of ``INSERT OR IGNORE``, but acceptance must still pass.
        counts = _sqlite_counts(conn)
        counts["candidate_tasks_skipped"] = int(ct_counts.get("skipped", 0))
        counts["planner_events_skipped"] = int(pe_counts.get("skipped", 0))

    # Acceptance: rows_inserted + rows_already_present (skipped because of
    # idempotent re-run) must equal the legacy total. We detect this by
    # counting the canonical projection rather than relying on insert
    # rowcounts (PG INSERT ... SELECT does not differentiate between "I
    # just inserted" and "row already existed" in a single result set).
    final_ct = counts["candidate_tasks_inserted"]
    final_pe = counts["planner_events_inserted"]
    legacy_ct = counts["candidate_tasks_total"]
    legacy_pe = counts["planner_events_total"]
    if final_ct < legacy_ct or final_pe < legacy_pe:
        # Fail loudly — Constraint #5 says unparseable rows are tolerated,
        # but a missing row means the SQL/CASE didn't cover an input.
        raise RuntimeError(
            "Phase 2.1 backfill incomplete: "
            f"candidate_tasks projected={final_ct} of {legacy_ct}, "
            f"planner_events projected={final_pe} of {legacy_pe}"
        )

    _write_audit(conn, kind="phase_2_1_backfill", payload=counts)
    logger.info("[phase_2_1] backfill complete: %s", counts)


def downgrade() -> None:
    conn = op.get_bind()

    # Delete via the explicit legacy_source marker so we never touch
    # rows that producers wrote natively after the migration. Both
    # branches use ``metadata::jsonb`` so they work on PG; SQLite tests
    # use ``json_extract`` instead.
    _ensure_audit_table(conn)

    if _is_postgres(conn):
        ct_deleted = _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='candidates' "
            "   AND metadata::jsonb ->> 'legacy_source' = 'candidate_tasks'",
        )
        pe_deleted = _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='comms' "
            "   AND metadata::jsonb ->> 'legacy_source' = 'communication_planner_events'",
        )
        op.execute(sa.text(
            "DELETE FROM activities "
            " WHERE source_module='candidates' "
            "   AND metadata::jsonb ->> 'legacy_source' = 'candidate_tasks'"
        ))
        op.execute(sa.text(
            "DELETE FROM activities "
            " WHERE source_module='comms' "
            "   AND metadata::jsonb ->> 'legacy_source' = 'communication_planner_events'"
        ))
    else:
        ct_deleted = _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='candidates' "
            "   AND json_extract(metadata, '$.legacy_source') = 'candidate_tasks'",
        )
        pe_deleted = _count(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module='comms' "
            "   AND json_extract(metadata, '$.legacy_source') = 'communication_planner_events'",
        )
        op.execute(sa.text(
            "DELETE FROM activities "
            " WHERE source_module='candidates' "
            "   AND json_extract(metadata, '$.legacy_source') = 'candidate_tasks'"
        ))
        op.execute(sa.text(
            "DELETE FROM activities "
            " WHERE source_module='comms' "
            "   AND json_extract(metadata, '$.legacy_source') = 'communication_planner_events'"
        ))

    _write_audit(
        conn,
        kind="phase_2_1_downgrade",
        payload={
            "candidate_tasks_deleted": ct_deleted,
            "planner_events_deleted": pe_deleted,
        },
    )
    logger.info(
        "[phase_2_1] downgrade complete: candidate_tasks=%d planner_events=%d",
        ct_deleted, pe_deleted,
    )
