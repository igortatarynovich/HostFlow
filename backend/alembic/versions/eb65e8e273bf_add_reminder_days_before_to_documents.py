"""add reminder_days_before to documents

Revision ID: eb65e8e273bf
Revises: 0e741c3987f5
Create Date: 2025-09-13 10:11:32.915076+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb65e8e273bf'
down_revision: Union[str, Sequence[str], None] = '0e741c3987f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("documents")}
    if "reminder_days_before" in columns:
        return
    op.add_column(
        'documents',
        sa.Column('reminder_days_before', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("documents")}
    if "reminder_days_before" in columns:
        op.drop_column('documents', 'reminder_days_before')
