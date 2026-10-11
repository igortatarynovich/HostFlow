"""Intended start date and work system on the live terms snapshot.

Revision ID: 202610080001_hr_employment_terms_preparation
Revises: 202610070001_hr_ready_to_start

The feature graph already names these columns under a revision that
collides with the live Ready to Start head. This revision is the live
child of that head. Existing rows are not backfilled.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610080001_hr_employment_terms_preparation"
down_revision: Union[str, None] = "202610070001_hr_ready_to_start"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("hr_employment_terms", sa.Column("work_system", sa.String(255), nullable=True))
    op.add_column("hr_employment_terms", sa.Column("intended_start_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("hr_employment_terms", "intended_start_date")
    op.drop_column("hr_employment_terms", "work_system")
