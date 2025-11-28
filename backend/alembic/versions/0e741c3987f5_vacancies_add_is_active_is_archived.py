"""vacancies add is_active & is_archived

Revision ID: 0e741c3987f5
Revises: 20250912_companies_vacancies_mvp
Create Date: 2025-09-13 06:30:08.078731+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e741c3987f5'
down_revision: Union[str, Sequence[str], None] = '20250912_companies_vacancies_mvp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    """Return True if the given column exists on the table.

    Uses Inspector.get_columns for cross-version compatibility because
    Inspector.has_column may not be available in all SQLAlchemy versions.
    """
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        columns = [c["name"] for c in insp.get_columns(table)]
    except Exception:
        # Table might not exist yet
        return False
    return column in columns


def upgrade() -> None:
    """Upgrade schema (idempotent for partially applied SQLite DDL)."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if not _has_column('vacancies', 'is_active'):
        op.add_column(
            'vacancies',
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        if not is_sqlite:
            op.alter_column('vacancies', 'is_active', server_default=None)

    if not _has_column('vacancies', 'is_archived'):
        op.add_column(
            'vacancies',
            sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        if not is_sqlite:
            op.alter_column('vacancies', 'is_archived', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the columns if they exist
    if _has_column('vacancies', 'is_archived'):
        op.drop_column('vacancies', 'is_archived')
    if _has_column('vacancies', 'is_active'):
        op.drop_column('vacancies', 'is_active')
