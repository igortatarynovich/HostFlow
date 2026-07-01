"""Leave only one Citronex tenant_link: the one linked to Citronex Trans Logistic Sp. z o.o.

Remove all other tenant_links with client_tenant_id = Citronex, keeping only the row
whose handoff_include_company_id points to the company named like 'Citronex Trans Logistic%'
(or the known company id from earlier migrations).

Revision ID: 202602081001
Revises: 202602081000
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op


revision: str = "202602081001"
down_revision: Union[str, Sequence[str], None] = "202602081000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CITRONEX_TENANT_ID = "517319d0-b53e-493d-9ac8-40f23091a35d"
# Company id used in 202602080006 for Citronex (fallback if name match fails)
CITRONEX_TRANS_LOGISTIC_COMPANY_ID = "ed6e7c5b-bc2f-4194-969d-e78d72d63e69"


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    # Keep one link: where handoff_include_company_id = company named "Citronex Trans Logistic..." or known id.
    # Delete all other tenant_links for Citronex (client_tenant_id = Citronex).
    op.execute(f"""
        DELETE FROM tenant_links
        WHERE client_tenant_id = '{CITRONEX_TENANT_ID}'
          AND id NOT IN (
            SELECT id FROM tenant_links
            WHERE client_tenant_id = '{CITRONEX_TENANT_ID}'
              AND (
                handoff_include_company_id = (
                  SELECT id FROM companies
                  WHERE name ILIKE '%%Citronex Trans Logistic%%'
                  LIMIT 1
                )
                OR handoff_include_company_id = '{CITRONEX_TRANS_LOGISTIC_COMPANY_ID}'
              )
            ORDER BY id
            LIMIT 1
          )
    """)


def downgrade() -> None:
    # Cannot restore deleted links; no-op.
    pass
