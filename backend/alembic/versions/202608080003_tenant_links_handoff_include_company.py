"""Add handoff_include_company_id to tenant_links for client tenants

When a client tenant (e.g. Citronex) has handoffs created to a company (client_company_id)
instead of to the tenant (client_tenant_id), this column allows those handoffs to appear
in the "На обработку" list for the tenant admin.

Revision ID: 202608080003
Revises: 202608080002
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202608080003"
down_revision: Union[str, None] = "202608080002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant_links",
        sa.Column("handoff_include_company_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_tenant_links_handoff_include_company",
        "tenant_links",
        "companies",
        ["handoff_include_company_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Link Citronex tenant to CITRONEX company for handoff visibility
    op.execute("""
        UPDATE tenant_links
        SET handoff_include_company_id = 'ed6e7c5b-bc2f-4194-969d-e78d72d63e69'
        WHERE client_tenant_id = '517319d0-b53e-493d-9ac8-40f23091a35d'
        AND handoff_include_company_id IS NULL
    """)


def downgrade() -> None:
    op.drop_constraint(
        "fk_tenant_links_handoff_include_company",
        "tenant_links",
        type_="foreignkey",
    )
    op.drop_column("tenant_links", "handoff_include_company_id")
