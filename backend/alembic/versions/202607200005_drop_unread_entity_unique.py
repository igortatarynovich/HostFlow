"""Drop unread entity unique index — episode-level idempotency replaces it.

Revision ID: 202607200005_drop_entity_uq
Revises: 202607200004_notif_idempotency
Create Date: 2026-07-20

``uq_notifications_unread_entity_identity`` allowed only one unread row per
(entity, type). That blocked a new SLA episode after the lead moved stages
while an older unread notification still existed.

Dedup is now owned by ``idempotency_key`` (episode / breach id).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607200005_drop_entity_uq"
down_revision: Union[str, Sequence[str], None] = "202607200004_notif_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "uq_notifications_unread_entity_identity"


def upgrade() -> None:
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


def downgrade() -> None:
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
