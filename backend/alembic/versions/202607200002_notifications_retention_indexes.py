"""Retention helper indexes for notifications TTL purge.

Revision ID: 202607200002_notif_retention_idx
Revises: 202607200001_notif_unread_idx
Create Date: 2026-07-20

Supports batched DELETE by ``created_at`` for:
* read + non-critical
* unread + non-critical
* critical

Uses CREATE INDEX CONCURRENTLY IF NOT EXISTS so emergency / partial
manual creates do not break upgrade.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607200002_notif_retention_idx"
down_revision: Union[str, Sequence[str], None] = "202607200001_notif_unread_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEXES = (
    (
        "ix_notifications_retention_read_created",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_retention_read_created "
        "ON notifications (created_at) "
        "WHERE is_read = true AND (priority IS NULL OR priority <> 'critical')",
    ),
    (
        "ix_notifications_retention_unread_created",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_retention_unread_created "
        "ON notifications (created_at) "
        "WHERE is_read = false AND (priority IS NULL OR priority <> 'critical')",
    ),
    (
        "ix_notifications_retention_critical_created",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_retention_critical_created "
        "ON notifications (created_at) "
        "WHERE priority = 'critical'",
    ),
)


def _has_index(conn: sa.Connection, table: str, index: str) -> bool:
    if table not in set(sa.inspect(conn).get_table_names()):
        return False
    try:
        return index in {ix["name"] for ix in sa.inspect(conn).get_indexes(table)}
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    if "notifications" not in set(sa.inspect(bind).get_table_names()):
        return

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            for _name, ddl in _INDEXES:
                op.execute(sa.text(ddl))
        return

    for name, _ddl in _INDEXES:
        if not _has_index(bind, "notifications", name):
            # SQLite: approximate with plain created_at index (predicate optional).
            op.create_index(name, "notifications", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if "notifications" not in set(sa.inspect(bind).get_table_names()):
        return

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            for name, _ddl in _INDEXES:
                op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {name}"))
        return

    for name, _ddl in _INDEXES:
        if _has_index(bind, "notifications", name):
            op.drop_index(name, table_name="notifications")
