"""Unique unread identity index for entity-bound notifications.

Revision ID: 202607200003_notif_dedupe_uq
Revises: 202607200002_notif_retention_idx
Create Date: 2026-07-20

Requires duplicates to be collapsed first (retention job / CLI). Uses
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607200003_notif_dedupe_uq"
down_revision: Union[str, Sequence[str], None] = "202607200002_notif_retention_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "uq_notifications_unread_entity_identity"


def upgrade() -> None:
    bind = op.get_bind()
    if "notifications" not in set(sa.inspect(bind).get_table_names()):
        return

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(
                sa.text(
                    f"""
                    CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {_INDEX}
                    ON notifications (
                      tenant_id, user_id, type, channel,
                      related_entity_type, related_entity_id
                    )
                    WHERE is_read = false AND related_entity_id IS NOT NULL
                    """
                )
            )
        return

    insp = sa.inspect(bind)
    existing = {ix["name"] for ix in insp.get_indexes("notifications")}
    if _INDEX not in existing:
        op.create_index(
            _INDEX,
            "notifications",
            [
                "tenant_id",
                "user_id",
                "type",
                "channel",
                "related_entity_type",
                "related_entity_id",
            ],
            unique=True,
            sqlite_where=sa.text("is_read = 0 AND related_entity_id IS NOT NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "notifications" not in set(sa.inspect(bind).get_table_names()):
        return
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {_INDEX}"))
        return
    insp = sa.inspect(bind)
    existing = {ix["name"] for ix in insp.get_indexes("notifications")}
    if _INDEX in existing:
        op.drop_index(_INDEX, table_name="notifications")
