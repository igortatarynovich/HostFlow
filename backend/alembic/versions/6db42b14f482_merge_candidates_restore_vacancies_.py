"""merge candidates restore + vacancies employment_type

Revision ID: 6db42b14f482
Revises: d278bee1e7f4, eccdaaa20c9c
Create Date: 2025-09-13 05:50:00.385420+00:00

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = '6db42b14f482'
down_revision: Union[str, Sequence[str], None] = ('d278bee1e7f4', 'eccdaaa20c9c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
