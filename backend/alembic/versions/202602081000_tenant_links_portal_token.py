"""Add portal_token and portal_expires_at to tenant_links for client portal access.

Revision ID: 202602081000
Revises: 202602080011
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202602081000"
down_revision: Union[str, Sequence[str], None] = "202602080011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant_links",
        sa.Column("portal_token", sa.String(64), nullable=True),
    )
    op.add_column(
        "tenant_links",
        sa.Column("portal_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tenant_links_portal_token", "tenant_links", ["portal_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tenant_links_portal_token", table_name="tenant_links")
    op.drop_column("tenant_links", "portal_expires_at")
    op.drop_column("tenant_links", "portal_token")
