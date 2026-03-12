"""Leave only 2 accepted handoffs to Citronex tenant; rest become company-only.

Client sees full data only for candidates with accepted handoff TO tenant (client_tenant_id).
If many handoffs have client_tenant_id = Citronex, too many show full PII. This migration
keeps the 2 most recently accepted handoffs as "to tenant" and sets the rest to "to company"
(client_tenant_id = NULL, client_company_id = linked company) so only 2 get full data.

Revision ID: 202602080010
Revises: 202602080009
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op


revision: str = "202602080010"
down_revision: Union[str, Sequence[str], None] = "202602080009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CITRONEX_TENANT_ID = "517319d0-b53e-493d-9ac8-40f23091a35d"
# Company from tenant_links handoff_include_company_id for Citronex
CITRONEX_LINKED_COMPANY_ID = "ed6e7c5b-bc2f-4194-969d-e78d72d63e69"


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    # Of accepted handoffs with client_tenant_id = Citronex, keep only the 2 most recent
    # (by reviewed_at). Set the rest to company-only (client_tenant_id = NULL, client_company_id = X).
    op.execute(f"""
        WITH keep_ids AS (
            SELECT id FROM candidate_handoffs
            WHERE client_tenant_id = '{CITRONEX_TENANT_ID}' AND status = 'accepted'
            ORDER BY reviewed_at DESC NULLS LAST
            LIMIT 2
        )
        UPDATE candidate_handoffs h
        SET client_tenant_id = NULL,
            client_company_id = '{CITRONEX_LINKED_COMPANY_ID}'
        WHERE h.client_tenant_id = '{CITRONEX_TENANT_ID}'
          AND h.status = 'accepted'
          AND h.id NOT IN (SELECT id FROM keep_ids)
    """)


def downgrade() -> None:
    # We do not restore client_tenant_id on downgrade.
    pass
