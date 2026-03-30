"""document_policies.own_company_id for §2.4 multi–own-company scope

Revision ID: 202603291500_doc_pol_oc
Revises: 202603291400_svc_ord_oc
Create Date: 2026-03-29

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202603291500_doc_pol_oc"
down_revision: Union[str, None] = "202603291400_svc_ord_oc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn: sa.Connection, table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in sa.inspect(conn).get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    conn = op.get_bind()
    if not sa.inspect(conn).has_table("document_policies"):
        return
    if _has_column(conn, "document_policies", "own_company_id"):
        return
    with op.batch_alter_table("document_policies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("own_company_id", sa.String(length=36), nullable=True))
    op.create_index(
        op.f("ix_document_policies_own_company_id"),
        "document_policies",
        ["own_company_id"],
        unique=False,
    )


def downgrade() -> None:
    conn = op.get_bind()
    if not sa.inspect(conn).has_table("document_policies"):
        return
    if not _has_column(conn, "document_policies", "own_company_id"):
        return
    op.drop_index(op.f("ix_document_policies_own_company_id"), table_name="document_policies")
    with op.batch_alter_table("document_policies", schema=None) as batch_op:
        batch_op.drop_column("own_company_id")
