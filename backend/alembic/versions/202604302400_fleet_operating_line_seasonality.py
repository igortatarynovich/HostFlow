"""Fleet operating lines: optional per-line monthly seasonality factors (12 × multiplier).

Revision ID: 202604302400_fleet_operating_line_seasonality
Revises: 202604302300_candidate_stage_employment_pending

This revision id is fixed: some databases already recorded it in ``alembic_version``
when an earlier branch applied the migration from another checkout. The upgrade is
idempotent so re-running is safe.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302400_fleet_operating_line_seasonality"
down_revision: Union[str, None] = "202604302300_candidate_stage_employment_pending"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    op.execute(
        """
        DO $body$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'fleet_operating_lines'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'fleet_operating_lines'
                  AND column_name = 'seasonality_month_factors'
            ) THEN
                ALTER TABLE fleet_operating_lines
                    ADD COLUMN seasonality_month_factors JSONB;
            END IF;
        END
        $body$;
        """
    )


def downgrade() -> None:
    if not _is_postgres():
        return
    op.execute(
        """
        DO $body$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'fleet_operating_lines'
            ) THEN
                ALTER TABLE fleet_operating_lines
                    DROP COLUMN IF EXISTS seasonality_month_factors;
            END IF;
        END
        $body$;
        """
    )
