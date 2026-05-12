"""Legacy fleet_vehicles: relax registration_number NOT NULL, backfill registration_plate.

Older DBs kept registration_number as the canonical plate with NOT NULL while product
API uses registration_plate. ORM inserts omitted registration_number → 500 on create.

Revision ID: 202604302530_fleet_vehicles_regnum_nullable
Revises: 202604302520_fleet_work_models_notes
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302530_fleet_vehicles_regnum_nullable"
down_revision: Union[str, None] = "202604302520_fleet_work_models_notes"
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
    if not _has_column(bind, "fleet_vehicles", "registration_number"):
        return
    op.execute(
        sa.text(
            """
            UPDATE fleet_vehicles
            SET registration_plate = registration_number
            WHERE (registration_plate IS NULL OR TRIM(registration_plate) = '')
              AND registration_number IS NOT NULL
              AND TRIM(registration_number) <> ''
            """
        )
    )
    op.execute(sa.text("ALTER TABLE fleet_vehicles ALTER COLUMN registration_number DROP NOT NULL"))


def downgrade() -> None:
    if not _is_postgres():
        return
    bind = op.get_bind()
    if not _has_column(bind, "fleet_vehicles", "registration_number"):
        return
    op.execute(
        sa.text(
            """
            UPDATE fleet_vehicles
            SET registration_number = COALESCE(
                NULLIF(TRIM(registration_number), ''),
                NULLIF(TRIM(registration_plate), ''),
                '-'
            )
            WHERE registration_number IS NULL
               OR TRIM(registration_number) = ''
            """
        )
    )
    op.execute(sa.text("ALTER TABLE fleet_vehicles ALTER COLUMN registration_number SET NOT NULL"))
