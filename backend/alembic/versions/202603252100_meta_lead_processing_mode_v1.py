"""meta_lead_settings.leads_processing_mode_v1 — Manual / Assisted / Automatic (§2.10)

Revision ID: 202603252100_meta_proc_mode
Revises: 202603252000_stage_contract
Create Date: 2026-03-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202603252100_meta_proc_mode"
down_revision: Union[str, None] = "202603252000_stage_contract"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meta_lead_settings",
        sa.Column("leads_processing_mode_v1", sa.String(length=24), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meta_lead_settings", "leads_processing_mode_v1")
