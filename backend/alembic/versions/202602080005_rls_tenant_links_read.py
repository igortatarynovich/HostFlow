"""RLS on tenant_links: agency and client can read their links.

Ensures when client runs list query, subqueries in candidates/vacancies RLS
can read the link where client_tenant_id = app.tenant_id.

Revision ID: 202602080005
Revises: 202602080004
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202602080005"
down_revision: Union[str, Sequence[str], None] = "202602080004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    op.execute("ALTER TABLE tenant_links ENABLE ROW LEVEL SECURITY;")

    # Agency can read links where they are the agency
    op.execute("""
        CREATE POLICY rls_tenant_links_agency ON tenant_links
        FOR SELECT
        USING (agency_tenant_id::uuid = current_setting('app.tenant_id')::uuid);
    """)
    # Client can read links where they are the client (for RLS subqueries in candidates/vacancies)
    op.execute("""
        CREATE POLICY rls_tenant_links_client ON tenant_links
        FOR SELECT
        USING (client_tenant_id::uuid = current_setting('app.tenant_id')::uuid);
    """)


def downgrade() -> None:
    if not _is_postgres():
        return
    op.execute("DROP POLICY IF EXISTS rls_tenant_links_client ON tenant_links;")
    op.execute("DROP POLICY IF EXISTS rls_tenant_links_agency ON tenant_links;")
    op.execute("ALTER TABLE tenant_links DISABLE ROW LEVEL SECURITY;")
