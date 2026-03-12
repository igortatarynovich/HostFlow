"""Ensure Citronex has links for all agency companies with vacancies (idempotent).

Migration 202602080007 only inserts links when at least one row already exists with
client_tenant_id = Citronex and handoff_include_company_id IS NOT NULL. If that row
was created only later by 202602080008, 007 inserted 0 rows and the client sees only
handoff/own candidates (e.g. 6). This migration runs the same INSERT as 007 so that
after 008 has created the first link, we add the remaining (agency, Citronex, company_id)
for every company with vacancies. Safe to run multiple times (NOT EXISTS prevents duplicates).

Revision ID: 202602080009
Revises: 202602080008
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op


revision: str = "202602080009"
down_revision: Union[str, Sequence[str], None] = "202602080008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CITRONEX_TENANT_ID = "517319d0-b53e-493d-9ac8-40f23091a35d"


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    # Same logic as 202602080007: add a link for every (agency, Citronex, company_id)
    # where the agency has vacancies in that company and the link does not exist yet.
    # After 202602080008 we have at least one row with client_tenant_id = Citronex,
    # so this INSERT will find rows and add any missing companies.
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
    # Optionally remove links added by this migration (keep at least one per 007 downgrade behavior).
    # We do not remove to avoid breaking the client view.
    pass
