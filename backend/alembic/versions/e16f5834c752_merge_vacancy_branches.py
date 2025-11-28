"""merge vacancy branches

Revision ID: e16f5834c752
Revises: 202601010001, 00bfe5b21d89
Create Date: 2025-10-29 17:41:56.851097+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e16f5834c752'
down_revision: Union[str, Sequence[str], None] = ('202601010001', '00bfe5b21d89')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
