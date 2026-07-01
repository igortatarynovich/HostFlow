"""meta_lead_settings.leads_auto_convert_on_fit_v1 — §2.4 safeguard for automatic conversion

Revision ID: 202603291200_meta_ac_fit
Revises: 202603281200_ar_priority
Create Date: 2026-03-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202603291200_meta_ac_fit"
down_revision: Union[str, None] = "202603281200_ar_priority"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meta_lead_settings",
        sa.Column(
            "leads_auto_convert_on_fit_v1",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("meta_lead_settings", "leads_auto_convert_on_fit_v1")
