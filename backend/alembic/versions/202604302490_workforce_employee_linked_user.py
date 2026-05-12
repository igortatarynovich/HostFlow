"""Workforce employee optional link to workspace User (org units via user memberships).

Revision ID: 202604302490_workforce_linked_user
Revises: 202604302480_license_fleet_seats
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302490_workforce_linked_user"
down_revision: Union[str, None] = "202604302480_license_fleet_seats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _index_names(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return set()
    return {ix["name"] for ix in insp.get_indexes(table) if ix.get("name")}


def upgrade() -> None:
    bind = op.get_bind()
    uid = sa.String(36)
    tbl = "workforce_employees"
    col = "linked_user_id"
    ix_name = "ix_workforce_employees_linked_user_id"
    if not _has_column(bind, tbl, col):
        op.add_column(
            tbl,
            sa.Column(
                col,
                uid,
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if ix_name not in _index_names(bind, tbl):
        op.create_index(ix_name, tbl, [col])


def downgrade() -> None:
    bind = op.get_bind()
    tbl = "workforce_employees"
    ix_name = "ix_workforce_employees_linked_user_id"
    col = "linked_user_id"
    if sa.inspect(bind).has_table(tbl) and ix_name in _index_names(bind, tbl):
        op.drop_index(ix_name, table_name=tbl)
    if _has_column(bind, tbl, col):
        op.drop_column(tbl, col)
