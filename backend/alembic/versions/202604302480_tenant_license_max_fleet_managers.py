"""tenant_licenses: max_fleet_managers seat cap (separate from recruiters).

Revision ID: 202604302480_license_fleet_seats
Revises: 202604302470_user_role_fleet_manager
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302480_license_fleet_seats"
down_revision: Union[str, None] = "202604302470_user_role_fleet_manager"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    return any(col["name"] == column for col in insp.get_columns(table))


def upgrade() -> None:
    conn = op.get_bind()
    if not sa.inspect(conn).has_table("tenant_licenses"):
        return
    if not _has_column(conn, "tenant_licenses", "max_fleet_managers"):
        op.add_column(
            "tenant_licenses",
            sa.Column("max_fleet_managers", sa.Integer(), nullable=False, server_default="0"),
        )
    op.execute(sa.text("UPDATE tenant_licenses SET max_fleet_managers = max_recruiters"))


def downgrade() -> None:
    conn = op.get_bind()
    if sa.inspect(conn).has_table("tenant_licenses") and _has_column(conn, "tenant_licenses", "max_fleet_managers"):
        op.drop_column("tenant_licenses", "max_fleet_managers")
