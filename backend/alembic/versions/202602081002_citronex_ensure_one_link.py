"""Ensure at least one Citronex tenant_link exists so client sees candidates.

If 202602081001 deleted all links (e.g. company name no longer matched), restore one link
with handoff_include_company_id = known Citronex company, using agency_tenant_id from handoffs.

Revision ID: 202602081002
Revises: 202602081001
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op


revision: str = "202602081002"
down_revision: Union[str, Sequence[str], None] = "202602081001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CITRONEX_TENANT_ID = "517319d0-b53e-493d-9ac8-40f23091a35d"
CITRONEX_TRANS_LOGISTIC_COMPANY_ID = "ed6e7c5b-bc2f-4194-969d-e78d72d63e69"


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    # If no tenant_link for Citronex exists, insert one so the client sees candidates.
    # agency_tenant_id: from handoffs, or from company.tenant_id for the linked company.
    op.execute(f"""
        INSERT INTO tenant_links (id, agency_tenant_id, client_tenant_id, handoff_include_company_id, status, created_at, updated_at)
        SELECT
            gen_random_uuid()::text,
            COALESCE(
                (SELECT agency_tenant_id FROM candidate_handoffs
                 WHERE client_tenant_id = '{CITRONEX_TENANT_ID}' OR client_company_id = '{CITRONEX_TRANS_LOGISTIC_COMPANY_ID}'
                 LIMIT 1),
                (SELECT tenant_id FROM companies WHERE id = '{CITRONEX_TRANS_LOGISTIC_COMPANY_ID}' LIMIT 1)
            ),
            '{CITRONEX_TENANT_ID}',
            '{CITRONEX_TRANS_LOGISTIC_COMPANY_ID}',
            'active',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM (SELECT 1) one
        WHERE NOT EXISTS (SELECT 1 FROM tenant_links WHERE client_tenant_id = '{CITRONEX_TENANT_ID}')
          AND (SELECT tenant_id FROM companies WHERE id = '{CITRONEX_TRANS_LOGISTIC_COMPANY_ID}' LIMIT 1) IS NOT NULL
    """)


def downgrade() -> None:
    pass
