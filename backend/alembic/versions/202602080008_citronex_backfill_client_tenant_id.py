"""Backfill client_tenant_id on tenant_links that have only client_company_id.

For client-with-tenant (e.g. Citronex) to see full candidate list and have PII mask
applied, tenant_links must have client_tenant_id = their tenant and handoff_include_company_id
set. If a link was created with only client_company_id, scope and RLS miss it.
This migration sets client_tenant_id on such rows for the known Citronex company.

Revision ID: 202602080008
Revises: 202602080007
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op


revision: str = "202602080008"
down_revision: Union[str, Sequence[str], None] = "202602080007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CITRONEX_TENANT_ID = "517319d0-b53e-493d-9ac8-40f23091a35d"
# Company used in 202602080006 as handoff_include_company_id for Citronex
CITRONEX_LINKED_COMPANY_ID = "ed6e7c5b-bc2f-4194-969d-e78d72d63e69"


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    # 1) Remove redundant company-only rows when a (agency, client_tenant_id, handoff_include_company_id)
    #    row already exists (would violate uq_tenant_links_agency_client_tenant_company if we updated).
    op.execute(f"""
        DELETE FROM tenant_links tl
        WHERE tl.client_company_id = '{CITRONEX_LINKED_COMPANY_ID}'
          AND (tl.client_tenant_id IS NULL OR tl.client_tenant_id = '')
          AND EXISTS (
            SELECT 1 FROM tenant_links t2
            WHERE t2.agency_tenant_id = tl.agency_tenant_id
              AND t2.client_tenant_id = '{CITRONEX_TENANT_ID}'
              AND t2.handoff_include_company_id = '{CITRONEX_LINKED_COMPANY_ID}'
              AND t2.id != tl.id
          )
    """)
    # 2) Convert remaining company-only links to client_tenant_id + handoff_include_company_id.
    #    Clear client_company_id to satisfy ck_tenant_links_client_exactly_one.
    op.execute(f"""
        UPDATE tenant_links
        SET client_tenant_id = '{CITRONEX_TENANT_ID}',
            handoff_include_company_id = COALESCE(handoff_include_company_id, '{CITRONEX_LINKED_COMPANY_ID}'),
            client_company_id = NULL
        WHERE client_company_id = '{CITRONEX_LINKED_COMPANY_ID}'
          AND (client_tenant_id IS NULL OR client_tenant_id = '')
    """)


def downgrade() -> None:
    # We do not clear client_tenant_id on downgrade to avoid breaking the client view.
    pass
