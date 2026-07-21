"""Allow FK cascade DELETE on acquisition_activity_events; keep direct DELETE blocked.

Revision ID: 202607220002_acq_3e_imm
Revises: 202607220001_acq_3e_act
Create Date: 2026-07-21

Direct application UPDATE/DELETE remain forbidden. Parent Campaign/Flight
CASCADE deletes (trigger depth > 1) may remove orphaned audit rows so hard
delete of Campaign does not fail after Timeline instrumentation.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

# NOTE: revision id kept ≤32 chars.
revision: str = "202607220002_acq_3e_imm"
down_revision: Union[str, None] = "202607220001_acq_3e_act"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    insp = inspect(bind)
    if "acquisition_activity_events" not in insp.get_table_names():
        return
    op.execute(
        """
        CREATE OR REPLACE FUNCTION acquisition_activity_events_immutable()
        RETURNS trigger AS $$
        BEGIN
          -- Block every UPDATE.
          IF TG_OP = 'UPDATE' THEN
            RAISE EXCEPTION
              'acquisition_activity_events is append-only '
              '(no UPDATE of any column, no DELETE)';
          END IF;
          -- Block direct DELETE; allow FK CASCADE from parent delete.
          IF TG_OP = 'DELETE' AND pg_trigger_depth() <= 1 THEN
            RAISE EXCEPTION
              'acquisition_activity_events is append-only '
              '(no UPDATE of any column, no DELETE)';
          END IF;
          RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    insp = inspect(bind)
    if "acquisition_activity_events" not in insp.get_table_names():
        return
    op.execute(
        """
        CREATE OR REPLACE FUNCTION acquisition_activity_events_immutable()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION
            'acquisition_activity_events is append-only '
            '(no UPDATE of any column, no DELETE)';
        END;
        $$ LANGUAGE plpgsql
        """
    )
