"""merge heads hr_document_control_tasks and document_reference_m2

Revision ID: 09ded874040a
Revises: 202605250001_hr_document_control_tasks, 202608130003_merge_document_reference_m2_head
Create Date: 2026-05-25 11:45:04.910170+00:00

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '09ded874040a'
down_revision: Union[str, Sequence[str], None] = ('202605250001_hr_document_control_tasks', '202608130003_merge_document_reference_m2_head')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
