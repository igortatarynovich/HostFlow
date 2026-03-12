"""Ensure Citronex tenant has type=company and link has client_tenant_id + handoff_include_company_id.

Client with own tenant (e.g. Citronex) must have tenants.type = 'company' so
is_client_tenant returns True. For full candidate list they need a tenant_link
with client_tenant_id = their tenant and handoff_include_company_id = company.

Revision ID: 202602080006
Revises: 202602080005
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202602080006"
down_revision: Union[str, Sequence[str], None] = "202602080005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    bind = op.get_bind()
    if _is_postgres():
        # Ensure tenants named like Citronex have type = company (for is_client_tenant)
        op.execute("""
            UPDATE tenants
            SET type = 'company'
            WHERE (name ILIKE '%citronex%' OR id::text = '517319d0-b53e-493d-9ac8-40f23091a35d')
              AND type != 'company'
        """)
        # Ensure link for Citronex tenant has handoff_include_company_id (202608080003 may have set it; re-apply if null)
        op.execute("""
            UPDATE tenant_links tl
            SET handoff_include_company_id = 'ed6e7c5b-bc2f-4194-969d-e78d72d63e69'
            WHERE tl.client_tenant_id = '517319d0-b53e-493d-9ac8-40f23091a35d'
              AND tl.handoff_include_company_id IS NULL
        """)
    else:
        # SQLite
        op.execute("""
            UPDATE tenants
            SET type = 'company'
            WHERE (LOWER(name) LIKE '%citronex%' OR id = '517319d0-b53e-493d-9ac8-40f23091a35d')
              AND type != 'company'
        """)


def downgrade() -> None:
    pass
