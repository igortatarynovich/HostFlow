"""Add pull_field_data_from_graph flag to meta lead settings

Revision ID: 202601020001
Revises: 202601010001
Create Date: 2026-01-02 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202601020001"
down_revision = "202601010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meta_lead_settings",
        sa.Column("pull_field_data_from_graph", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    # backfill existing rows with true
    op.execute("UPDATE meta_lead_settings SET pull_field_data_from_graph = true WHERE pull_field_data_from_graph IS NULL")


def downgrade() -> None:
    op.drop_column("meta_lead_settings", "pull_field_data_from_graph")
