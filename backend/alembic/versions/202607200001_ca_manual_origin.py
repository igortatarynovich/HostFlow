"""ClientAccount Origins: manual_creation columns + creation_origin_v1.

Revision ID: 202607200001_ca_manual_origin
Revises: 202607190004_thread_result_link_c1
Create Date: 2026-07-20
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607200001_ca_manual_origin"
down_revision: Union[str, Sequence[str], None] = "202607190004_thread_result_link_c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("client_accounts")} if "client_accounts" in insp.get_table_names() else set()

    json_type = postgresql.JSONB() if dialect == "postgresql" else sa.JSON()

    if "origin_type" not in cols:
        op.add_column(
            "client_accounts",
            sa.Column("origin_type", sa.String(length=64), nullable=True),
        )
    if "creation_ref" not in cols:
        op.add_column(
            "client_accounts",
            sa.Column("creation_ref", sa.String(length=36), nullable=True),
        )
    if "idempotency_key" not in cols:
        op.add_column(
            "client_accounts",
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        )
    if "creation_origin_v1" not in cols:
        op.add_column(
            "client_accounts",
            sa.Column("creation_origin_v1", json_type, nullable=True),
        )

    op.create_index(
        "ix_client_accounts_tenant_origin_type",
        "client_accounts",
        ["tenant_id", "origin_type"],
        unique=False,
    )
    # Partial unique indexes — PostgreSQL; SQLite tests use create_all / ignore if unsupported.
    if dialect == "postgresql":
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_client_accounts_tenant_idempotency "
                "ON client_accounts (tenant_id, idempotency_key) "
                "WHERE idempotency_key IS NOT NULL"
            )
        )
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_client_accounts_tenant_creation_ref "
                "ON client_accounts (tenant_id, creation_ref) "
                "WHERE creation_ref IS NOT NULL"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS uq_client_accounts_tenant_creation_ref"))
        op.execute(sa.text("DROP INDEX IF EXISTS uq_client_accounts_tenant_idempotency"))
    op.drop_index("ix_client_accounts_tenant_origin_type", table_name="client_accounts")
    for col in ("creation_origin_v1", "idempotency_key", "creation_ref", "origin_type"):
        try:
            op.drop_column("client_accounts", col)
        except Exception:
            pass
