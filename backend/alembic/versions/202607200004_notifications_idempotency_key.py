"""Add notifications.idempotency_key for runaway-proof inserts.

Revision ID: 202607200004_notif_idempotency
Revises: 202607200003_notif_dedupe_uq
Create Date: 2026-07-20
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607200004_notif_idempotency"
down_revision: Union[str, Sequence[str], None] = "202607200003_notif_dedupe_uq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "uq_notifications_idempotency_key"


def upgrade() -> None:
    bind = op.get_bind()
    if "notifications" not in set(sa.inspect(bind).get_table_names()):
        return
    cols = {c["name"] for c in sa.inspect(bind).get_columns("notifications")}
    if "idempotency_key" not in cols:
        op.add_column(
            "notifications",
            sa.Column("idempotency_key", sa.String(length=191), nullable=True),
        )

    if bind.dialect.name == "postgresql":
        # Backfill stable keys for entity-bound unread rows (best effort).
        op.execute(
            sa.text(
                """
                UPDATE notifications
                SET idempotency_key = left(
                  type || ':' || tenant_id || ':' || user_id || ':' ||
                  coalesce(related_entity_type, '') || ':' || coalesce(related_entity_id, ''),
                  191
                )
                WHERE idempotency_key IS NULL
                  AND related_entity_id IS NOT NULL
                  AND is_read = false
                """
            )
        )
        # Drop conflicting duplicates keeping newest before unique index.
        for _ in range(500):
            result = bind.execute(
                sa.text(
                    """
                    WITH ranked AS (
                      SELECT id,
                             ROW_NUMBER() OVER (
                               PARTITION BY idempotency_key
                               ORDER BY created_at DESC, id DESC
                             ) AS rn
                      FROM notifications
                      WHERE idempotency_key IS NOT NULL
                    ),
                    doomed AS (SELECT id FROM ranked WHERE rn > 1 LIMIT 20000)
                    DELETE FROM notifications n USING doomed d WHERE n.id = d.id
                    """
                )
            )
            if int(result.rowcount or 0) == 0:
                break

        with op.get_context().autocommit_block():
            op.execute(
                sa.text(
                    f"""
                    CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {_INDEX}
                    ON notifications (idempotency_key)
                    WHERE idempotency_key IS NOT NULL
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
            ["idempotency_key"],
            unique=True,
            sqlite_where=sa.text("idempotency_key IS NOT NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "notifications" not in set(sa.inspect(bind).get_table_names()):
        return
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {_INDEX}"))
    else:
        insp = sa.inspect(bind)
        existing = {ix["name"] for ix in insp.get_indexes("notifications")}
        if _INDEX in existing:
            op.drop_index(_INDEX, table_name="notifications")
    cols = {c["name"] for c in sa.inspect(bind).get_columns("notifications")}
    if "idempotency_key" in cols:
        op.drop_column("notifications", "idempotency_key")
