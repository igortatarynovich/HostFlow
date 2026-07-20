"""Repair: ensure communication_inbound_unresolved.resolved_* columns exist.

C0.2 migration ``202607200002_comm_inbound_unresolved`` creates the full table,
but production-like DBs may have been Alembic-stamped with a partial table
(missing resolved_* audit columns). This revision is idempotent and safe to run
when columns already exist (manual repair or clean upgrade path).

Revision ID: 202607200007_comm_inbound_unresolved_resolved_cols_repair
Revises: 202607200006_comm_thread_work_version
Create Date: 2026-07-20
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607200007_comm_inbound_unresolved_resolved_cols_repair"
down_revision: RevisionType = "202607200006_comm_thread_work_version"
branch_labels: RevisionType = None
depends_on: RevisionType = None

TABLE = "communication_inbound_unresolved"

# (column_name, SQLAlchemy column)
_RESOLVED_COLUMNS: tuple[tuple[str, sa.Column], ...] = (
    ("resolved_by_user_id", sa.Column("resolved_by_user_id", sa.String(length=36), nullable=True)),
    ("resolved_at", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)),
    ("resolved_entity_type", sa.Column("resolved_entity_type", sa.String(length=64), nullable=True)),
    ("resolved_entity_id", sa.Column("resolved_entity_id", sa.String(length=120), nullable=True)),
    ("resolved_thread_id", sa.Column("resolved_thread_id", sa.String(length=36), nullable=True)),
)


def _existing_columns(bind: sa.Connection, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    existing = _existing_columns(bind, TABLE)
    if not existing:
        # Table missing entirely — leave creation to C0.2; nothing to repair.
        return

    dialect = bind.dialect.name
    for name, column in _RESOLVED_COLUMNS:
        if name in existing:
            continue
        if dialect == "postgresql":
            # Concurrent-safe / stamp-drift safe path used elsewhere in this repo.
            coltype = {
                "resolved_by_user_id": "VARCHAR(36)",
                "resolved_at": "TIMESTAMPTZ",
                "resolved_entity_type": "VARCHAR(64)",
                "resolved_entity_id": "VARCHAR(120)",
                "resolved_thread_id": "VARCHAR(36)",
            }[name]
            op.execute(sa.text(f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS {name} {coltype}"))
        else:
            op.add_column(TABLE, column)


def downgrade() -> None:
    # Non-destructive repair: do not drop columns that may hold resolution audit.
    return
