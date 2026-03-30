"""meta_lead_settings.generic_inbound_webhook_secret — §2.11 public JSON webhook ingest (Team+)

Revision ID: 202603271300_generic_inbound_wh
Revises: 202603271200_cfv_created_at
Create Date: 2026-03-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202603271300_generic_inbound_wh"
down_revision: Union[str, None] = "202603271200_cfv_created_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meta_lead_settings",
        sa.Column("generic_inbound_webhook_secret", sa.String(length=128), nullable=True),
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_meta_lead_settings_generic_inbound_wh_secret
        ON meta_lead_settings (generic_inbound_webhook_secret)
        WHERE generic_inbound_webhook_secret IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_meta_lead_settings_generic_inbound_wh_secret")
    op.drop_column("meta_lead_settings", "generic_inbound_webhook_secret")
