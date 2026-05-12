"""Legacy fleet_trailers / fleet_drivers: relax NOT NULL columns used by park ORM.

- Trailers: same registration_number vs registration_plate story as fleet_vehicles.
- Trailers: trailer_type NOT NULL + explicit NULL from ORM breaks INSERT (product schema allows optional type).
- Drivers: first_name / last_name NOT NULL while API allows omitting names (display_code only).

Revision ID: 202604302531_fleet_trailers_drivers_legacy
Revises: 202604302530_fleet_vehicles_regnum_nullable
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302531_fleet_trailers_drivers_legacy"
down_revision: Union[str, None] = "202604302530_fleet_vehicles_regnum_nullable"
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

    if _has_column(bind, "fleet_trailers", "registration_number"):
        op.execute(
            sa.text(
                """
                UPDATE fleet_trailers
                SET registration_plate = registration_number
                WHERE (registration_plate IS NULL OR TRIM(registration_plate) = '')
                  AND registration_number IS NOT NULL
                  AND TRIM(registration_number) <> ''
                """
            )
        )
        op.execute(sa.text("ALTER TABLE fleet_trailers ALTER COLUMN registration_number DROP NOT NULL"))

    if _has_column(bind, "fleet_trailers", "trailer_type"):
        op.execute(sa.text("ALTER TABLE fleet_trailers ALTER COLUMN trailer_type DROP NOT NULL"))

    if _has_column(bind, "fleet_drivers", "first_name"):
        op.execute(sa.text("ALTER TABLE fleet_drivers ALTER COLUMN first_name DROP NOT NULL"))
    if _has_column(bind, "fleet_drivers", "last_name"):
        op.execute(sa.text("ALTER TABLE fleet_drivers ALTER COLUMN last_name DROP NOT NULL"))


def downgrade() -> None:
    if not _is_postgres():
        return
    bind = op.get_bind()

    if _has_column(bind, "fleet_trailers", "registration_number"):
        op.execute(
            sa.text(
                """
                UPDATE fleet_trailers
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
        op.execute(sa.text("ALTER TABLE fleet_trailers ALTER COLUMN registration_number SET NOT NULL"))

    if _has_column(bind, "fleet_trailers", "trailer_type"):
        op.execute(
            sa.text(
                """
                UPDATE fleet_trailers
                SET trailer_type = COALESCE(NULLIF(TRIM(trailer_type), ''), 'other')
                WHERE trailer_type IS NULL OR TRIM(trailer_type) = ''
                """
            )
        )
        op.execute(
            sa.text(
                "ALTER TABLE fleet_trailers ALTER COLUMN trailer_type SET NOT NULL"
            )
        )
        op.execute(
            sa.text(
                "ALTER TABLE fleet_trailers ALTER COLUMN trailer_type SET DEFAULT 'other'::character varying"
            )
        )

    if _has_column(bind, "fleet_drivers", "first_name"):
        op.execute(
            sa.text(
                """
                UPDATE fleet_drivers
                SET first_name = COALESCE(NULLIF(TRIM(first_name), ''), '-')
                WHERE first_name IS NULL OR TRIM(first_name) = ''
                """
            )
        )
        op.execute(sa.text("ALTER TABLE fleet_drivers ALTER COLUMN first_name SET NOT NULL"))
    if _has_column(bind, "fleet_drivers", "last_name"):
        op.execute(
            sa.text(
                """
                UPDATE fleet_drivers
                SET last_name = COALESCE(NULLIF(TRIM(last_name), ''), '-')
                WHERE last_name IS NULL OR TRIM(last_name) = ''
                """
            )
        )
        op.execute(sa.text("ALTER TABLE fleet_drivers ALTER COLUMN last_name SET NOT NULL"))
