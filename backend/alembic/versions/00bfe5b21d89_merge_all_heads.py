"""merge all heads

Revision ID: 00bfe5b21d89
Revises: 202512010300_expand_reminder_entity_id, 202512010300_ruleset_versioning_foundation, 202512010310_meta_leads_pipeline, 202512150001_documents_module_restructure, 202512150001_unify_documents_module, 202512210001_documents_type_dedup
Create Date: 2025-10-28 16:07:04.264771+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00bfe5b21d89'
down_revision: Union[str, Sequence[str], None] = ('202512010300_expand_reminder_entity_id', '202512010300_ruleset_versioning_foundation', '202512010310_meta_leads_pipeline', '202512150001_documents_module_restructure', '202512150001_unify_documents_module', '202512210001_documents_type_dedup')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
