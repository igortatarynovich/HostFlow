"""funnel_stages.stage_contract_v1 — owner_role, required_actions, sla, auto_rules

Revision ID: 202603252000_stage_contract
Revises: 202603251400_stripe_webhook_log
Create Date: 2026-03-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202603252000_stage_contract"
down_revision: Union[str, None] = "202603251400_stripe_webhook_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
    op.add_column("funnel_stages", sa.Column("stage_contract_v1", json_type, nullable=True))


def downgrade() -> None:
    op.drop_column("funnel_stages", "stage_contract_v1")
