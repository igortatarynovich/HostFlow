"""Partial indexes for unread notifications poll + dedupe paths.

Revision ID: 202607200001_notif_unread_idx
Revises: 202607190004_thread_result_link_c1
Create Date: 2026-07-20

Hot path (Topbar / GET /api/v1/notifications):
  WHERE tenant_id = ? AND user_id = ? AND is_read = false
  ORDER BY created_at DESC LIMIT N

Dedupe path (create_notification):
  WHERE tenant_id AND user_id AND type AND channel
    AND created_at >= ? AND is_read = false
  ORDER BY created_at DESC

Without a partial index that leads with (tenant_id, user_id, created_at),
Postgres falls back to tenant-wide scans + heapsort (observed ~5s on a
user with ~2.6M unread rows).

Indexes are created with IF NOT EXISTS (and CONCURRENTLY on Postgres)
so a prior emergency CREATE INDEX does not break upgrade.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607200001_notif_unread_idx"
down_revision: Union[str, Sequence[str], None] = "202607190004_thread_result_link_c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# List / poll: supports ORDER BY created_at without type/channel filters.
_LIST_INDEX = "ix_notifications_unread_user_created"
_LIST_SQL = (
    f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_LIST_INDEX} "
    "ON notifications (tenant_id, user_id, created_at DESC) "
    "WHERE is_read = false"
)

# Dedupe + typed lookups (requested composite).
_DEDUPE_INDEX = "ix_notifications_unread_user_type_channel_created"
_DEDUPE_SQL = (
    f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_DEDUPE_INDEX} "
    "ON notifications (tenant_id, user_id, type, channel, created_at DESC) "
    "WHERE is_read = false"
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
        # CONCURRENTLY cannot run inside a transaction.
        with op.get_context().autocommit_block():
            op.execute(sa.text(_LIST_SQL))
            op.execute(sa.text(_DEDUPE_SQL))
        return

    # SQLite / other: non-concurrent create when missing (ASC is fine; btree is bidirectional).
    if not _has_index(bind, "notifications", _LIST_INDEX):
        op.create_index(
            _LIST_INDEX,
            "notifications",
            ["tenant_id", "user_id", "created_at"],
            sqlite_where=sa.text("is_read = 0"),
        )
    if not _has_index(bind, "notifications", _DEDUPE_INDEX):
        op.create_index(
            _DEDUPE_INDEX,
            "notifications",
            ["tenant_id", "user_id", "type", "channel", "created_at"],
            sqlite_where=sa.text("is_read = 0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "notifications" not in set(sa.inspect(bind).get_table_names()):
        return

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {_DEDUPE_INDEX}"))
            op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {_LIST_INDEX}"))
        return

    if _has_index(bind, "notifications", _DEDUPE_INDEX):
        op.drop_index(_DEDUPE_INDEX, table_name="notifications")
    if _has_index(bind, "notifications", _LIST_INDEX):
        op.drop_index(_LIST_INDEX, table_name="notifications")
