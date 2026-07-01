"""own and client companies tables

Revision ID: 202608120001
Revises: 202608110004_services_cost_basis
Create Date: 2026-08-12 00:01:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202608120001"
down_revision: Union[str, Sequence[str], None] = "202608110004_services_cost_basis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, table: str) -> bool:
    insp = sa.inspect(conn)
    return table in insp.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not _has_table(conn, "own_companies"):
        op.create_table(
            "own_companies",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("legal_name", sa.String(length=255), nullable=True),
            sa.Column("tax_id", sa.String(length=64), nullable=True),
            sa.Column("phone", sa.String(length=64), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("website", sa.String(length=255), nullable=True),
            sa.Column("country_code", sa.String(length=2), nullable=True),
            sa.Column("country", sa.String(length=64), nullable=True),
            sa.Column("city", sa.String(length=128), nullable=True),
            sa.Column("address", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.String(length=2000), nullable=True),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("contacts", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("extra", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("bank_details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_own_companies_tenant_id", "own_companies", ["tenant_id"])
        op.create_index("ix_own_companies_tenant_name", "own_companies", ["tenant_id", "name"])
        op.create_index("ix_own_companies_tenant_tax_id", "own_companies", ["tenant_id", "tax_id"])

    if not _has_table(conn, "client_companies"):
        op.create_table(
            "client_companies",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("legal_name", sa.String(length=255), nullable=True),
            sa.Column("tax_id", sa.String(length=64), nullable=True),
            sa.Column("phone", sa.String(length=64), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("website", sa.String(length=255), nullable=True),
            sa.Column("country_code", sa.String(length=2), nullable=True),
            sa.Column("country", sa.String(length=64), nullable=True),
            sa.Column("city", sa.String(length=128), nullable=True),
            sa.Column("address", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.String(length=2000), nullable=True),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("contacts", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("extra", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_client_companies_tenant_id", "client_companies", ["tenant_id"])
        op.create_index("ix_client_companies_tenant_name", "client_companies", ["tenant_id", "name"])
        op.create_index("ix_client_companies_tenant_tax_id", "client_companies", ["tenant_id", "tax_id"])

    # Ensure JSON columns use JSONB on PostgreSQL where supported.
    if conn.dialect.name == "postgresql":
        # OwnCompany
        for col in ("contacts", "extra", "bank_details"):
            try:
                op.alter_column("own_companies", col, type_=sa.dialects.postgresql.JSONB(), existing_type=sa.JSON())
            except Exception:
                pass
        # ClientCompany
        for col in ("contacts", "extra"):
            try:
                op.alter_column("client_companies", col, type_=sa.dialects.postgresql.JSONB(), existing_type=sa.JSON())
            except Exception:
                pass


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "client_companies"):
        op.drop_index("ix_client_companies_tenant_tax_id", table_name="client_companies")
        op.drop_index("ix_client_companies_tenant_name", table_name="client_companies")
        op.drop_index("ix_client_companies_tenant_id", table_name="client_companies")
        op.drop_table("client_companies")
    if _has_table(conn, "own_companies"):
        op.drop_index("ix_own_companies_tenant_tax_id", table_name="own_companies")
        op.drop_index("ix_own_companies_tenant_name", table_name="own_companies")
        op.drop_index("ix_own_companies_tenant_id", table_name="own_companies")
        op.drop_table("own_companies")

