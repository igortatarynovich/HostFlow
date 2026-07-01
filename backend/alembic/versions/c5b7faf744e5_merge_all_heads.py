"""merge_all_heads

Revision ID: c5b7faf744e5
Revises: 202602040004_merge_funnels_and_profile_funnel
Create Date: 2026-02-07 17:05:48.545370+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5b7faf744e5'
down_revision: Union[str, Sequence[str], None] = '202602040004_merge_funnels_and_profile_funnel'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
