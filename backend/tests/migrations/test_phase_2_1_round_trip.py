"""Round-trip test for Phase 2.1 backfill migration.

Validates the SQLite branch of
``backend/alembic/versions/202607150004_planner_tasks_into_activities.py``
end-to-end:

* Bootstraps an empty in-memory SQLite database with the canonical
  ``activities`` shape (the bits the migration needs) plus the legacy
  ``candidate_tasks`` and ``communication_planner_events`` tables.
* Runs the migration's ``upgrade()`` against this connection and
  asserts the rows arrived in ``activities`` with the right
  ``type`` / ``source_module`` / ``related_entity_*`` /
  ``metadata.legacy_source`` / ``metadata.legacy.*`` shape.
* Asserts the audit table holds a ``phase_2_1_backfill`` row whose
  payload counts match the inputs.
* Runs ``upgrade()`` a **second** time and asserts no duplicates
  appear (idempotency).
* Runs ``downgrade()`` and asserts every backfilled row in
  ``activities`` (matched by ``metadata.legacy_source``) is gone, and
  a ``phase_2_1_downgrade`` audit row is recorded.

We deliberately do **not** use the Alembic CLI (the project's
``alembic/env.py`` rejects SQLite DSNs by design — Postgres is the
production target). Instead we install an ``Operations`` proxy backed
by our SQLite connection, which is the documented way to unit-test
migration code outside of an actual ``alembic upgrade`` invocation.
"""

from __future__ import annotations

import importlib
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext


_TENANT = "11111111-1111-1111-1111-111111111111"
_USER_OK = "22222222-2222-2222-2222-222222222222"


# ---------------------------------------------------------------------------
# DB bootstrap — create the slice of schema the migration touches.
# ---------------------------------------------------------------------------


_ACTIVITIES_DDL = """
CREATE TABLE activities (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    company_id TEXT,
    type TEXT NOT NULL,
    source_module TEXT,
    source TEXT,
    related_entity_type TEXT NOT NULL,
    related_entity_id TEXT NOT NULL,
    title TEXT,
    description TEXT,
    message TEXT,
    owner_id TEXT,
    assigned_to_user_id TEXT,
    created_by_user_id TEXT,
    priority TEXT,
    channel TEXT,
    starts_at TIMESTAMP,
    due_at TIMESTAMP NOT NULL,
    reminder_at TIMESTAMP,
    duration_minutes INTEGER,
    snoozed_until TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    sent_at TIMESTAMP,
    sla_due_at TIMESTAMP,
    sla_status TEXT,
    recurrence_json TEXT,
    status TEXT NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
)
"""

_USERS_DDL = """
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL
)
"""

_CANDIDATE_TASKS_DDL = """
CREATE TABLE candidate_tasks (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    due_on TEXT,
    priority TEXT,
    assigned_to TEXT,
    completed INTEGER DEFAULT 0,
    meta TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
)
"""

_PLANNER_EVENTS_DDL = """
CREATE TABLE communication_planner_events (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    start_at TIMESTAMP NOT NULL,
    end_at TIMESTAMP,
    all_day INTEGER NOT NULL DEFAULT 0,
    owner_id TEXT,
    assignee_id TEXT,
    entity_type TEXT,
    entity_id TEXT,
    linked_candidate_id TEXT,
    linked_company_id TEXT,
    source TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
)
"""


def _bootstrap(conn: sa.Connection) -> None:
    for ddl in (_USERS_DDL, _ACTIVITIES_DDL, _CANDIDATE_TASKS_DDL, _PLANNER_EVENTS_DDL):
        conn.exec_driver_sql(ddl)
    conn.exec_driver_sql(
        "INSERT INTO users (id, tenant_id) VALUES (:i, :t)",
        {"i": _USER_OK, "t": _TENANT},
    )


def _seed_legacy(conn: sa.Connection, *, now: datetime) -> dict[str, str]:
    """Insert one fixture row per logical case we care about. Returns ID map."""
    ids: dict[str, str] = {f"key_{i}": str(uuid.uuid4()) for i in range(20)}

    # candidate_tasks ---------------------------------------------------
    candidate_id = str(uuid.uuid4())
    iso_due_str = (now + timedelta(days=2)).date().isoformat()  # YYYY-MM-DD

    conn.execute(
        sa.text(
            "INSERT INTO candidate_tasks "
            "  (id, tenant_id, candidate_id, title, description, status, "
            "   due_on, priority, assigned_to, completed, meta, "
            "   created_at, updated_at) "
            "VALUES (:id, :t, :c, :title, :d, :s, :due, :p, :a, :done, :m, :ca, :ua)"
        ),
        [
            # 1. Happy path — ISO due_on, valid UUID assignee in users.
            {
                "id": ids["key_0"], "t": _TENANT, "c": candidate_id,
                "title": "Reach out", "d": "Initial contact",
                "s": "open", "due": iso_due_str, "p": "high",
                "a": _USER_OK, "done": 0, "m": json.dumps({"x": 1}),
                "ca": now, "ua": now,
            },
            # 2. Missing due_on — must fall back to updated_at + flag.
            {
                "id": ids["key_1"], "t": _TENANT, "c": candidate_id,
                "title": "No deadline", "d": None,
                "s": "open", "due": None, "p": None,
                "a": "alice@example.com", "done": 0, "m": None,
                "ca": now, "ua": now,
            },
            # 3. Unparseable due_on — must NOT fail; raw stored in metadata.
            {
                "id": ids["key_2"], "t": _TENANT, "c": candidate_id,
                "title": "Bad date", "d": None,
                "s": "in_progress", "due": "next-tuesday", "p": None,
                "a": None, "done": 0, "m": None,
                "ca": now, "ua": now,
            },
            # 4. Completed flag wins over status text.
            {
                "id": ids["key_3"], "t": _TENANT, "c": candidate_id,
                "title": "Done flag", "d": None,
                "s": "open", "due": iso_due_str, "p": None,
                "a": None, "done": 1, "m": None,
                "ca": now, "ua": now,
            },
            # 5. Cancelled status text.
            {
                "id": ids["key_4"], "t": _TENANT, "c": candidate_id,
                "title": "Cancelled", "d": None,
                "s": "cancelled", "due": iso_due_str, "p": "low",
                "a": None, "done": 0, "m": None,
                "ca": now, "ua": now,
            },
            # 6. UUID assignee but NOT in users table — drop it, raw to metadata.
            {
                "id": ids["key_5"], "t": _TENANT, "c": candidate_id,
                "title": "Phantom assignee", "d": None,
                "s": "open", "due": iso_due_str, "p": None,
                "a": str(uuid.uuid4()), "done": 0, "m": None,
                "ca": now, "ua": now,
            },
        ],
    )

    # communication_planner_events -------------------------------------
    company_id = str(uuid.uuid4())

    conn.execute(
        sa.text(
            "INSERT INTO communication_planner_events "
            "  (id, tenant_id, title, description, kind, status, priority, "
            "   start_at, end_at, all_day, owner_id, assignee_id, "
            "   entity_type, entity_id, linked_candidate_id, linked_company_id, "
            "   source, payload, created_at, updated_at) "
            "VALUES (:id, :t, :title, :d, :k, :s, :p, "
            "        :st, :en, :ad, :o, :ag, :et, :ei, :lc, :lo, "
            "        :src, :pl, :ca, :ua)"
        ),
        [
            # 7. Meeting — explicit entity, explicit company in payload.
            {
                "id": ids["key_6"], "t": _TENANT, "title": "Meeting",
                "d": "with team", "k": "meeting", "s": "planned", "p": "normal",
                "st": now, "en": now + timedelta(hours=1), "ad": 0,
                "o": _USER_OK, "ag": _USER_OK,
                "et": "company", "ei": company_id,
                "lc": None, "lo": company_id, "src": "manual",
                "pl": json.dumps({"company_id": company_id, "tags": ["a"]}),
                "ca": now, "ua": now,
            },
            # 8. Task kind — starts_at must be NULL (deadline-only).
            {
                "id": ids["key_7"], "t": _TENANT, "title": "Task PE",
                "d": None, "k": "task", "s": "in_progress", "p": "normal",
                "st": now, "en": None, "ad": 0,
                "o": None, "ag": _USER_OK,
                "et": "candidate", "ei": candidate_id,
                "lc": candidate_id, "lo": None, "src": "system",
                "pl": json.dumps({}),
                "ca": now, "ua": now,
            },
            # 9. Followup kind — starts_at NULL, type='follow_up'.
            {
                "id": ids["key_8"], "t": _TENANT, "title": "Followup",
                "d": None, "k": "followup", "s": "planned", "p": "normal",
                "st": now, "en": None, "ad": 0,
                "o": None, "ag": None,
                "et": None, "ei": None,
                "lc": candidate_id, "lo": None, "src": "manual",
                "pl": json.dumps({}),
                "ca": now, "ua": now,
            },
            # 10. Shift kind — type='custom', starts_at preserved.
            {
                "id": ids["key_9"], "t": _TENANT, "title": "Shift",
                "d": None, "k": "shift", "s": "done", "p": "normal",
                "st": now, "en": now + timedelta(hours=8), "ad": 1,
                "o": None, "ag": None,
                "et": None, "ei": None,
                "lc": None, "lo": None, "src": "manual",
                "pl": json.dumps({}),
                "ca": now, "ua": now,
            },
            # 11. Unresolved related entity — must get planner_event_legacy.
            {
                "id": ids["key_10"], "t": _TENANT, "title": "Orphan",
                "d": None, "k": "call", "s": "cancelled", "p": "normal",
                "st": now, "en": now + timedelta(minutes=15), "ad": 0,
                "o": None, "ag": None,
                "et": None, "ei": None,
                "lc": None, "lo": None, "src": "manual",
                "pl": json.dumps({}),
                "ca": now, "ua": now,
            },
        ],
    )

    return {**ids, "_candidate": candidate_id, "_company": company_id}


# ---------------------------------------------------------------------------
# Test driver.
# ---------------------------------------------------------------------------


def _load_migration():
    """Import the migration module by file path (it's not on sys.path)."""
    import sys
    from pathlib import Path
    versions_dir = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    sys.path.insert(0, str(versions_dir))
    try:
        return importlib.import_module("202607150004_planner_tasks_into_activities")
    finally:
        sys.path.pop(0)


def _row(conn: sa.Connection, sql: str, **bind):
    return conn.execute(sa.text(sql), bind).first()


def _scalar(conn: sa.Connection, sql: str, **bind) -> int | None:
    return conn.execute(sa.text(sql), bind).scalar()


def test_phase_2_1_backfill_round_trip():
    engine = sa.create_engine("sqlite:///:memory:", future=True)
    now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)

    with engine.begin() as conn:
        _bootstrap(conn)
        ids = _seed_legacy(conn, now=now)

    mod = _load_migration()

    # Run upgrade() with an alembic Operations proxy bound to our connection.
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mod.upgrade()

    # ---------------- assertions on backfilled rows ----------------
    with engine.connect() as conn:
        # Total: 6 candidate_tasks + 5 planner_events = 11.
        total = _scalar(conn, "SELECT count(*) FROM activities")
        assert total == 11, f"expected 11 backfilled rows, got {total}"

        # candidate_tasks projection ----------------------------------
        ct_row = _row(
            conn,
            "SELECT type, source_module, source, related_entity_type, "
            "       related_entity_id, status, due_at, assigned_to_user_id, "
            "       metadata, completed_at "
            "  FROM activities WHERE id = :id",
            id=ids["key_0"],
        )
        assert ct_row.type == "task"
        assert ct_row.source_module == "candidates"
        assert ct_row.source == "candidate_task_legacy"
        assert ct_row.related_entity_type == "candidate"
        assert ct_row.related_entity_id == ids["_candidate"]
        assert ct_row.status == "planned"
        assert ct_row.assigned_to_user_id == _USER_OK
        meta = json.loads(ct_row.metadata)
        assert meta["legacy_source"] == "candidate_tasks"
        assert "due_synthesized" not in meta.get("legacy", {})
        assert ct_row.completed_at is None

        # missing due_on row → due_synthesized + due_reason='missing_due_on'
        miss = _row(
            conn,
            "SELECT due_at, metadata FROM activities WHERE id = :id",
            id=ids["key_1"],
        )
        miss_meta = json.loads(miss.metadata)
        assert miss_meta["legacy"]["due_synthesized"] is True
        assert miss_meta["legacy"]["due_reason"] == "missing_due_on"
        assert miss_meta["legacy"]["assigned_to_raw"] == "alice@example.com"
        assert miss.due_at is not None

        # unparseable due_on row → due_reason='unparseable_due_on' + raw kept
        bad = _row(
            conn,
            "SELECT status, metadata FROM activities WHERE id = :id",
            id=ids["key_2"],
        )
        bad_meta = json.loads(bad.metadata)
        assert bad.status == "in_progress"
        assert bad_meta["legacy"]["due_reason"] == "unparseable_due_on"
        assert bad_meta["legacy"]["due_on_raw"] == "next-tuesday"

        # completed=1 wins over status='open'
        flagged = _row(
            conn,
            "SELECT status, completed_at FROM activities WHERE id = :id",
            id=ids["key_3"],
        )
        assert flagged.status == "done"
        assert flagged.completed_at is not None

        # cancelled
        canc = _row(
            conn,
            "SELECT status, completed_at FROM activities WHERE id = :id",
            id=ids["key_4"],
        )
        assert canc.status == "cancelled"
        assert canc.completed_at is None

        # phantom UUID assignee dropped (not in users)
        phantom = _row(
            conn,
            "SELECT assigned_to_user_id FROM activities WHERE id = :id",
            id=ids["key_5"],
        )
        assert phantom.assigned_to_user_id is None

        # planner_events projection ----------------------------------
        meeting = _row(
            conn,
            "SELECT type, source_module, related_entity_type, related_entity_id, "
            "       company_id, starts_at, due_at, duration_minutes, "
            "       owner_id, assigned_to_user_id, metadata "
            "  FROM activities WHERE id = :id",
            id=ids["key_6"],
        )
        assert meeting.type == "meeting"
        assert meeting.source_module == "comms"
        assert meeting.related_entity_type == "company"
        assert meeting.related_entity_id == ids["_company"]
        assert meeting.company_id == ids["_company"]
        assert meeting.starts_at is not None
        assert meeting.due_at is not None
        assert meeting.duration_minutes == 60
        assert meeting.owner_id == _USER_OK
        meeting_meta = json.loads(meeting.metadata)
        assert meeting_meta["legacy_source"] == "communication_planner_events"
        assert meeting_meta["planner"]["kind"] == "meeting"
        assert meeting_meta["tags"] == ["a"]

        task_pe = _row(
            conn,
            "SELECT type, status, starts_at FROM activities WHERE id = :id",
            id=ids["key_7"],
        )
        assert task_pe.type == "task"
        assert task_pe.status == "in_progress"
        assert task_pe.starts_at is None

        followup = _row(
            conn,
            "SELECT type, starts_at FROM activities WHERE id = :id",
            id=ids["key_8"],
        )
        assert followup.type == "follow_up"
        assert followup.starts_at is None

        shift = _row(
            conn,
            "SELECT type, starts_at, completed_at, duration_minutes, metadata "
            "  FROM activities WHERE id = :id",
            id=ids["key_9"],
        )
        assert shift.type == "custom"
        assert shift.starts_at is not None
        assert shift.completed_at is not None
        assert shift.duration_minutes == 480
        shift_meta = json.loads(shift.metadata)
        assert shift_meta["planner"]["kind"] == "shift"

        orphan = _row(
            conn,
            "SELECT related_entity_type, related_entity_id, cancelled_at, metadata "
            "  FROM activities WHERE id = :id",
            id=ids["key_10"],
        )
        assert orphan.related_entity_type == "planner_event_legacy"
        assert orphan.related_entity_id == ids["key_10"]
        assert orphan.cancelled_at is not None
        orphan_meta = json.loads(orphan.metadata)
        assert orphan_meta["legacy"]["unresolved_related_entity"] is True

    # ---------------- audit row ----------------
    with engine.connect() as conn:
        audit = _row(
            conn,
            "SELECT kind, payload FROM phase_2_1_backfill_audit "
            " WHERE kind = 'phase_2_1_backfill' "
            " ORDER BY id DESC LIMIT 1",
        )
        assert audit is not None
        payload = json.loads(audit.payload)
        assert payload["candidate_tasks_total"] == 6
        assert payload["planner_events_total"] == 5
        assert payload["candidate_tasks_inserted"] == 6
        assert payload["planner_events_inserted"] == 5
        assert payload["missing_due_on"] == 1
        assert payload["unparseable_due_on"] == 1
        # Both the "Shift" fixture (no entity_type, no linked_candidate_id)
        # and the "Orphan" fixture qualify as unresolved.
        assert payload["unresolved_related_entities"] == 2

    # ---------------- idempotency ----------------
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mod.upgrade()
    with engine.connect() as conn:
        total = _scalar(conn, "SELECT count(*) FROM activities")
        assert total == 11, f"idempotency broken: {total} rows after second upgrade"

    # ---------------- downgrade ----------------
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mod.downgrade()
    with engine.connect() as conn:
        survivors = _scalar(
            conn,
            "SELECT count(*) FROM activities "
            " WHERE source_module IN ('candidates','comms') "
            "   AND json_extract(metadata, '$.legacy_source') IN "
            "       ('candidate_tasks','communication_planner_events')",
        )
        assert survivors == 0
        # Downgrade audit row
        down_audit = _row(
            conn,
            "SELECT payload FROM phase_2_1_backfill_audit "
            " WHERE kind = 'phase_2_1_downgrade' ORDER BY id DESC LIMIT 1",
        )
        assert down_audit is not None
        down_payload = json.loads(down_audit.payload)
        assert down_payload["candidate_tasks_deleted"] == 6
        assert down_payload["planner_events_deleted"] == 5
