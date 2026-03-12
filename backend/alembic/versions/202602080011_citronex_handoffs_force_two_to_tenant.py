"""Force only 2 accepted handoffs to Citronex tenant (re-run fix if 010 didn't apply).

Idempotent: updates handoffs that still have client_tenant_id = Citronex except
the 2 most recent (by reviewed_at). Use OFFSET 2 so we update the 3rd, 4th, 5th...
Run this if after 202602080010 you still see 5 candidates with full PII.

Revision ID: 202602080011
Revises: 202602080010
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op


revision: str = "202602080011"
down_revision: Union[str, Sequence[str], None] = "202602080010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CITRONEX_TENANT_ID = "517319d0-b53e-493d-9ac8-40f23091a35d"
CITRONEX_LINKED_COMPANY_ID = "ed6e7c5b-bc2f-4194-969d-e78d72d63e69"


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    # Update all but the 2 most recent (by reviewed_at): set to company-only.
    op.execute(f"""
        UPDATE candidate_handoffs
        SET client_tenant_id = NULL,
            client_company_id = '{CITRONEX_LINKED_COMPANY_ID}'
        WHERE id IN (
            SELECT id FROM candidate_handoffs
            WHERE client_tenant_id = '{CITRONEX_TENANT_ID}' AND status = 'accepted'
            ORDER BY reviewed_at DESC NULLS LAST, id ASC
            OFFSET 2
        )
    """)


def downgrade() -> None:
    pass
