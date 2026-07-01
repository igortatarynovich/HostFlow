"""Legacy fleet_assignments: optional driver_id (product uses primary_driver_id).

Older tables required driver_id NOT NULL while ORM/API only set primary_driver_id → 500 on create.

Revision ID: 202604302532_fleet_assignments_legacy_driver
Revises: 202604302531_fleet_trailers_drivers_legacy
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302532_fleet_assignments_legacy_driver"
down_revision: Union[str, None] = "202604302531_fleet_trailers_drivers_legacy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if not _is_postgres():
        return
    bind = op.get_bind()
    if not _has_column(bind, "fleet_assignments", "driver_id"):
        return
    if _has_column(bind, "fleet_assignments", "primary_driver_id"):
        op.execute(
            sa.text(
                """
                UPDATE fleet_assignments
                SET primary_driver_id = driver_id
                WHERE primary_driver_id IS NULL
                  AND driver_id IS NOT NULL
                """
            )
        )
    op.execute(sa.text("ALTER TABLE fleet_assignments ALTER COLUMN driver_id DROP NOT NULL"))


def downgrade() -> None:
    if not _is_postgres():
        return
    bind = op.get_bind()
    if not _has_column(bind, "fleet_assignments", "driver_id"):
        return
    if _has_column(bind, "fleet_assignments", "primary_driver_id"):
        op.execute(
            sa.text(
                """
                UPDATE fleet_assignments
                SET driver_id = primary_driver_id
                WHERE driver_id IS NULL
                  AND primary_driver_id IS NOT NULL
                """
            )
        )
    op.execute(sa.text("ALTER TABLE fleet_assignments ALTER COLUMN driver_id SET NOT NULL"))
