"""merge heads before users/supervisor + memberships ts

Revision ID: 1e7d294073ca
Revises: 202512010200_admin_v2, 202502110002_add_is_active_to_document_types
Create Date: 2025-10-15 06:14:04.433808+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e7d294073ca'
down_revision: Union[str, Sequence[str], None] = ('202512010200_admin_v2', '202502110002_add_is_active_to_document_types')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
