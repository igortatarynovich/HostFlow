"""Add configurable meta lead field mapping to settings.

Revision ID: 202608110002
Revises: 202608110001
Create Date: 2026-08-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202608110002"
down_revision = "202608110001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
    op.add_column(
        "meta_lead_settings",
        sa.Column(
            "field_mapping",
            json_type,
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("meta_lead_settings", "field_mapping")
