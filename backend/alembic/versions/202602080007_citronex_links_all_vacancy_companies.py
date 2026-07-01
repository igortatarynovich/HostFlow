"""Let client tenant link to multiple companies; add Citronex links for all agency companies with vacancies.

Previously one row per (agency, client_tenant) — only one handoff_include_company_id. Now we allow
multiple rows per (agency, client_tenant) with different handoff_include_company_id so the client
sees candidates from all linked companies' vacancies.

Revision ID: 202602080007
Revises: 202602080006
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op


revision: str = "202602080007"
down_revision: Union[str, Sequence[str], None] = "202602080006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CITRONEX_TENANT_ID = "517319d0-b53e-493d-9ac8-40f23091a35d"


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    # 1) Allow multiple tenant_links per (agency, client_tenant) with different handoff_include_company_id
    op.execute("DROP INDEX IF EXISTS uq_tenant_links_agency_client_tenant;")
    op.execute("""
        CREATE UNIQUE INDEX uq_tenant_links_agency_client_tenant_company
        ON tenant_links (agency_tenant_id, client_tenant_id, handoff_include_company_id)
        WHERE client_tenant_id IS NOT NULL AND handoff_include_company_id IS NOT NULL
    """)

    # 2) For Citronex: add a link for every company (of the same agency) that has vacancies
    op.execute(f"""
        INSERT INTO tenant_links (id, agency_tenant_id, client_tenant_id, handoff_include_company_id, status, created_at, updated_at)
        SELECT
            gen_random_uuid()::text,
            sub.agency_tenant_id,
            sub.client_tenant_id,
            sub.company_id,
            'active',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM (
            SELECT DISTINCT tl.agency_tenant_id, tl.client_tenant_id, v.company_id
            FROM tenant_links tl
            JOIN vacancies v ON v.tenant_id = tl.agency_tenant_id
            WHERE tl.client_tenant_id = '{CITRONEX_TENANT_ID}'
              AND tl.handoff_include_company_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM tenant_links t2
                WHERE t2.agency_tenant_id = tl.agency_tenant_id
                  AND t2.client_tenant_id = tl.client_tenant_id
                  AND t2.handoff_include_company_id = v.company_id
              )
        ) sub
    """)


def downgrade() -> None:
    if not _is_postgres():
        return
    # Remove extra Citronex links (keep the original link with handoff_include_company_id from 202602080006)
    op.execute(f"""
        DELETE FROM tenant_links
        WHERE client_tenant_id = '{CITRONEX_TENANT_ID}'
          AND handoff_include_company_id != 'ed6e7c5b-bc2f-4194-969d-e78d72d63e69'
    """)
    # Restore original unique index
    op.execute("DROP INDEX IF EXISTS uq_tenant_links_agency_client_tenant_company;")
    op.execute("""
        CREATE UNIQUE INDEX uq_tenant_links_agency_client_tenant
        ON tenant_links (agency_tenant_id, client_tenant_id)
        WHERE client_tenant_id IS NOT NULL
    """)
