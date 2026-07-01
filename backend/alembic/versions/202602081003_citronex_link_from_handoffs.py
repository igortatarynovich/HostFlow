"""Restore Citronex tenant_link from handoffs if still missing.

202602081002 only inserts when company ed6e7c5b exists. If that company was removed
or never existed in this DB, use (agency, company) from any handoff to Citronex,
or any agency company with vacancies.

Revision ID: 202602081003
Revises: 202602081002
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op


revision: str = "202602081003"
down_revision: Union[str, Sequence[str], None] = "202602081002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CITRONEX_TENANT_ID = "517319d0-b53e-493d-9ac8-40f23091a35d"
CITRONEX_COMPANY_ID_FALLBACK = "ed6e7c5b-bc2f-4194-969d-e78d72d63e69"


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    # Still no tenant_link for Citronex? Insert one.
    # Prefer (agency, company) from handoff; else agency from handoff + any company with vacancies; else fallback company id.
    op.execute(f"""
        INSERT INTO tenant_links (id, agency_tenant_id, client_tenant_id, handoff_include_company_id, status, created_at, updated_at)
        SELECT
            gen_random_uuid()::text,
            COALESCE(
                (SELECT h.agency_tenant_id FROM candidate_handoffs h
                 WHERE h.client_tenant_id = '{CITRONEX_TENANT_ID}' LIMIT 1),
                (SELECT tenant_id FROM companies WHERE id = '{CITRONEX_COMPANY_ID_FALLBACK}' LIMIT 1)
            ),
            '{CITRONEX_TENANT_ID}',
            COALESCE(
                (SELECT h.client_company_id FROM candidate_handoffs h
                 WHERE h.client_tenant_id = '{CITRONEX_TENANT_ID}' AND h.client_company_id IS NOT NULL LIMIT 1),
                (SELECT c.id FROM companies c
                 INNER JOIN vacancies v ON v.company_id = c.id
                 WHERE c.tenant_id = (SELECT h2.agency_tenant_id FROM candidate_handoffs h2 WHERE h2.client_tenant_id = '{CITRONEX_TENANT_ID}' LIMIT 1)
                 LIMIT 1),
                (SELECT id FROM companies WHERE id = '{CITRONEX_COMPANY_ID_FALLBACK}' LIMIT 1)
            ),
            'active',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM (SELECT 1) one
        WHERE NOT EXISTS (SELECT 1 FROM tenant_links WHERE client_tenant_id = '{CITRONEX_TENANT_ID}')
          AND (
            (SELECT h.agency_tenant_id FROM candidate_handoffs h WHERE h.client_tenant_id = '{CITRONEX_TENANT_ID}' LIMIT 1) IS NOT NULL
            OR (SELECT tenant_id FROM companies WHERE id = '{CITRONEX_COMPANY_ID_FALLBACK}' LIMIT 1) IS NOT NULL
          )
    """)


def downgrade() -> None:
    pass
