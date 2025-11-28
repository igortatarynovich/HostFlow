"""create magic_links table

Revision ID: 202605010002
Revises: 202605010001
Create Date: 2025-05-01 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202605010002"
down_revision = "202605010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "magic_links",
        sa.Column("id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("candidate_id", sa.String(length=255), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=True),
        sa.Column("token", sa.String(length=128), nullable=False, unique=True),
        sa.Column("contact_type", sa.String(length=16), nullable=False),
        sa.Column("contact_value", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="apply"),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_magic_links_tenant_id", "magic_links", ["tenant_id"])
    op.create_index("ix_magic_links_token", "magic_links", ["token"])
    op.create_index("ix_magic_links_contact_value", "magic_links", ["contact_value"])
    op.create_index("ix_magic_links_candidate_id", "magic_links", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_magic_links_candidate_id", table_name="magic_links")
    op.drop_index("ix_magic_links_contact_value", table_name="magic_links")
    op.drop_index("ix_magic_links_token", table_name="magic_links")
    op.drop_index("ix_magic_links_tenant_id", table_name="magic_links")
    op.drop_table("magic_links")
