"""merge_heads

Revision ID: df8037565a0c
Revises: 202501040000_fix_status_model_enum_case, 202511261222, 202607010003_add_candidate_tags
Create Date: 2026-01-11 08:03:57.227890+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df8037565a0c'
down_revision: Union[str, Sequence[str], None] = ('202501040000_fix_status_model_enum_case', '202511261222', '202607010003_add_candidate_tags')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
