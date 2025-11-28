"""Merge RLS migration and scanner heads

Revision ID: 202511261202
Revises: 202511130001, 202511261201, 202606250004_set_fb_source_for_null_candidates
Create Date: 2025-11-26 12:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202511261202'
down_revision: Union[str, Sequence[str], None] = (
    '202511130001',  # add_scanner_tables
    '202511261201',  # enable_rls_for_all_tables
    '202606250004_set_fb_source_for_null_candidates',  # set_fb_source_for_null_candidates
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge revision - no schema changes."""
    pass


def downgrade() -> None:
    """Merge revision cannot be downgraded."""
    raise RuntimeError("Merge revision 202511261202 cannot be downgraded")

