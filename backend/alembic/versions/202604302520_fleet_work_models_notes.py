"""Add fleet_work_models.notes if missing (align with ORM / API).

Revision ID: 202604302520_fleet_work_models_notes
Revises: 202604302510_handoff_destination
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302520_fleet_work_models_notes"
down_revision: Union[str, None] = "202604302510_handoff_destination"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "fleet_work_models", "notes"):
        op.add_column("fleet_work_models", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "fleet_work_models", "notes"):
        op.drop_column("fleet_work_models", "notes")
