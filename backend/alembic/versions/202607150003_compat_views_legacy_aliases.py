"""compat_views_legacy_aliases — fix `reminders` / `user_notifications` views.

Revision ID: 202607150003_cvla
Revises: 202607150002_alv1
Create Date: 2026-05-09

Why this exists
---------------
Migration ``202607150002_alv1`` (Phase 1.3) created compatibility views
``reminders`` and ``user_notifications`` as ``CREATE VIEW reminders AS
SELECT * FROM activities`` (and analogous for notifications). The intent
of those views — per ADR-012 / Phase 1.3 plan §2.3 / Constraint #6 — is
to give legacy callers a *temporary* read surface in the **legacy column
names** (``entity_type``, ``entity_id``, ``payload``, ``assignee_id``,
``created_by``, ``remind_at``, ``event_type``) while the canonical tables
already use the renamed columns (``related_entity_type``, ``metadata``,
etc.).

A bare ``SELECT *`` does **not** rename columns, so any legacy SQL such
as ``SELECT entity_type FROM reminders`` or ``INSERT INTO reminders
(entity_type, ...)`` fails at parse time with::

    ERROR:  column "entity_type" of relation "reminders" does not exist

That breaks the contract of "compat view = looks like the old table".

This migration replaces the broken views with explicit projections that
re-alias every renamed column back to its legacy name. The
``INSTEAD OF`` trigger (``_activity_layer_v1_reject_legacy_write``) is
re-attached so writes are still rejected loudly (Constraint #6 —
read-only).

Idempotency
-----------
Both ``upgrade()`` and ``downgrade()`` use ``DROP VIEW IF EXISTS`` and
``DROP TRIGGER IF EXISTS`` so re-running is safe even after partial
failure. The plpgsql function ``_activity_layer_v1_reject_legacy_write``
is owned by ``202607150002_alv1`` and is **not** dropped here.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision: str = "202607150003_cvla"
down_revision: str = "202607150002_alv1"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _is_postgres(conn: sa.Connection) -> bool:
    return conn.dialect.name == "postgresql"


# Legacy column projections ---------------------------------------------------
# Order intentionally mirrors the original `reminders` table so legacy
# `SELECT *` callers keep their column ordering.
_REMINDERS_VIEW_SELECT = """\
SELECT
    id,
    tenant_id,
    type,
    related_entity_type  AS entity_type,
    related_entity_id    AS entity_id,
    due_at,
    status,
    message,
    metadata             AS payload,
    created_by_user_id   AS created_by,
    sent_at,
    cancelled_at,
    created_at,
    updated_at,
    title,
    description,
    owner_id,
    assigned_to_user_id  AS assignee_id,
    priority,
    channel,
    reminder_at          AS remind_at,
    snoozed_until,
    completed_at,
    recurrence_json,
    duration_minutes,
    source
FROM activities
"""

_USER_NOTIFICATIONS_VIEW_SELECT = """\
SELECT
    id,
    tenant_id,
    user_id,
    type                 AS event_type,
    related_entity_type  AS entity_type,
    related_entity_id    AS entity_id,
    metadata             AS payload,
    channel,
    is_read,
    delivered_at,
    read_at,
    created_at,
    updated_at,
    priority
FROM notifications
"""


def _drop_compat_objects(conn: sa.Connection) -> None:
    """Tear down view + INSTEAD OF trigger pair, idempotently."""
    if _is_postgres(conn):
        op.execute(sa.text(
            "DROP TRIGGER IF EXISTS reject_writes_user_notifications "
            "ON user_notifications"
        ))
        op.execute(sa.text(
            "DROP TRIGGER IF EXISTS reject_writes_reminders ON reminders"
        ))
    op.execute(sa.text("DROP VIEW IF EXISTS user_notifications"))
    op.execute(sa.text("DROP VIEW IF EXISTS reminders"))


def _create_aliased_views(conn: sa.Connection) -> None:
    """Create legacy-named views that project canonical columns."""
    op.execute(sa.text(f"CREATE VIEW reminders AS {_REMINDERS_VIEW_SELECT}"))
    op.execute(sa.text(
        f"CREATE VIEW user_notifications AS {_USER_NOTIFICATIONS_VIEW_SELECT}"
    ))


def _create_select_star_views(conn: sa.Connection) -> None:
    """Recreate the (broken) SELECT * views — used by downgrade only.

    This restores the exact post-202607150002_alv1 state so the
    Alembic graph is invertible.
    """
    op.execute(sa.text("CREATE VIEW reminders          AS SELECT * FROM activities"))
    op.execute(sa.text("CREATE VIEW user_notifications AS SELECT * FROM notifications"))


def _attach_reject_triggers(conn: sa.Connection) -> None:
    if not _is_postgres(conn):
        return
    op.execute(sa.text(
        "CREATE TRIGGER reject_writes_reminders "
        "  INSTEAD OF INSERT OR UPDATE OR DELETE ON reminders "
        "  FOR EACH ROW EXECUTE FUNCTION _activity_layer_v1_reject_legacy_write()"
    ))
    op.execute(sa.text(
        "CREATE TRIGGER reject_writes_user_notifications "
        "  INSTEAD OF INSERT OR UPDATE OR DELETE ON user_notifications "
        "  FOR EACH ROW EXECUTE FUNCTION _activity_layer_v1_reject_legacy_write()"
    ))


# ---------------------------------------------------------------------------
# migration
# ---------------------------------------------------------------------------

def upgrade() -> None:
    bind = op.get_bind()
    _drop_compat_objects(bind)
    _create_aliased_views(bind)
    _attach_reject_triggers(bind)


def downgrade() -> None:
    bind = op.get_bind()
    _drop_compat_objects(bind)
    _create_select_star_views(bind)
    _attach_reject_triggers(bind)
