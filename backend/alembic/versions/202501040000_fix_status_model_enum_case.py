"""Fix status_model enum case mismatch.

Revision ID: 202501040000_fix_status_model_enum_case
Revises: 202501030000_add_candidate_profiles_and_process_templates
Create Date: 2025-01-04 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '202501040000_fix_status_model_enum_case'
down_revision: Union[str, None] = '202501030000_add_candidate_profiles_and_process_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    """Check if we're using PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == 'postgresql'


def upgrade() -> None:
    """Update status_model values to uppercase to match Python enum."""
    if _is_postgres():
        # Обновляем значения в document_types
        op.execute("""
            UPDATE document_types 
            SET status_model = UPPER(status_model)
            WHERE status_model IS NOT NULL
            AND status_model != UPPER(status_model);
        """)
        
        # Обновляем значения в process_templates
        op.execute("""
            UPDATE process_templates 
            SET status_model = UPPER(status_model)
            WHERE status_model IS NOT NULL
            AND status_model != UPPER(status_model);
        """)


def downgrade() -> None:
    """Revert status_model values to lowercase."""
    if _is_postgres():
        # Возвращаем в нижний регистр (если нужно)
        op.execute("""
            UPDATE document_types 
            SET status_model = LOWER(status_model)
            WHERE status_model IS NOT NULL
            AND status_model != LOWER(status_model);
        """)
        
        op.execute("""
            UPDATE process_templates 
            SET status_model = LOWER(status_model)
            WHERE status_model IS NOT NULL
            AND status_model != LOWER(status_model);
        """)

