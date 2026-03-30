"""service_orders.own_company_id for multi–own-company scope (§2.4)

Revision ID: 202603291400_svc_ord_oc
Revises: 202603291300_client_co_mirror
Create Date: 2026-03-29

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202603291400_svc_ord_oc"
down_revision: Union[str, None] = "202603291300_client_co_mirror"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


def _has_column(conn: sa.Connection, table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in sa.inspect(conn).get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "service_orders") or _has_column(conn, "service_orders", "own_company_id"):
        return
    op.add_column(
        "service_orders",
        sa.Column("own_company_id", sa.String(length=36), nullable=True),
    )
    try:
        op.create_index("ix_service_orders_own_company_id", "service_orders", ["own_company_id"])
    except Exception:
        pass


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "service_orders") or not _has_column(conn, "service_orders", "own_company_id"):
        return
    try:
        op.drop_index("ix_service_orders_own_company_id", table_name="service_orders")
    except Exception:
        pass
    op.drop_column("service_orders", "own_company_id")
