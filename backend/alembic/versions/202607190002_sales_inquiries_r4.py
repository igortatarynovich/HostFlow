"""Runtime Split R4: sales_inquiries destination result table.

Revision ID: 202607190002_sales_inquiries_r4
Revises: 202607190001_forms_p24
Create Date: 2026-07-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202607190002_sales_inquiries_r4"
down_revision: Union[str, Sequence[str], None] = "202607190001_forms_p24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    if "sales_inquiries" in insp.get_table_names():
        return

    json_type = postgresql.JSONB() if dialect == "postgresql" else sa.JSON()

    op.create_table(
        "sales_inquiries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="public_intake"),
        sa.Column("own_company_id", sa.String(length=36), nullable=True),
        sa.Column("assignee_id", sa.String(length=36), nullable=True),
        sa.Column("entity_profile_code", sa.String(length=128), nullable=True),
        sa.Column("intake_source_profile_id", sa.String(length=36), nullable=True),
        sa.Column("form_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=191), nullable=True),
        sa.Column("meta", json_type, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_sales_inquiries_tenant_id", "sales_inquiries", ["tenant_id"])
    op.create_index("ix_sales_inquiries_lead_id", "sales_inquiries", ["lead_id"])
    op.create_index("ix_sales_inquiries_status", "sales_inquiries", ["status"])
    op.create_index("ix_sales_inquiries_own_company_id", "sales_inquiries", ["own_company_id"])
    op.create_index("ix_sales_inquiries_assignee_id", "sales_inquiries", ["assignee_id"])
    op.create_index(
        "ix_sales_inquiries_intake_source_profile_id",
        "sales_inquiries",
        ["intake_source_profile_id"],
    )
    op.create_index("ix_sales_inquiries_form_id", "sales_inquiries", ["form_id"])
    op.create_index("ix_sales_inquiries_idempotency_key", "sales_inquiries", ["idempotency_key"])

    if dialect == "postgresql":
        op.execute(
            """
            CREATE UNIQUE INDEX uq_sales_inquiries_tenant_lead
            ON sales_inquiries (tenant_id, lead_id)
            WHERE lead_id IS NOT NULL
            """
        )
        op.execute(
            """
            CREATE UNIQUE INDEX uq_sales_inquiries_tenant_idempotency
            ON sales_inquiries (tenant_id, idempotency_key)
            WHERE idempotency_key IS NOT NULL
            """
        )
        op.execute("ALTER TABLE sales_inquiries ENABLE ROW LEVEL SECURITY")
        op.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'sales_inquiries' AND policyname = 'tenant_isolation'
              ) THEN
                CREATE POLICY tenant_isolation ON sales_inquiries
                  USING (tenant_id = current_setting('app.tenant_id', true))
                  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
              END IF;
            END $$;
            """
        )
    else:
        op.create_index(
            "uq_sales_inquiries_tenant_lead",
            "sales_inquiries",
            ["tenant_id", "lead_id"],
            unique=True,
        )
        op.create_index(
            "uq_sales_inquiries_tenant_idempotency",
            "sales_inquiries",
            ["tenant_id", "idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    if "sales_inquiries" not in insp.get_table_names():
        return
    if dialect == "postgresql":
        op.execute("DROP INDEX IF EXISTS uq_sales_inquiries_tenant_idempotency")
        op.execute("DROP INDEX IF EXISTS uq_sales_inquiries_tenant_lead")
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON sales_inquiries")
    else:
        op.drop_index("uq_sales_inquiries_tenant_idempotency", table_name="sales_inquiries")
        op.drop_index("uq_sales_inquiries_tenant_lead", table_name="sales_inquiries")
    for name in (
        "ix_sales_inquiries_idempotency_key",
        "ix_sales_inquiries_form_id",
        "ix_sales_inquiries_intake_source_profile_id",
        "ix_sales_inquiries_assignee_id",
        "ix_sales_inquiries_own_company_id",
        "ix_sales_inquiries_status",
        "ix_sales_inquiries_lead_id",
        "ix_sales_inquiries_tenant_id",
    ):
        try:
            op.drop_index(name, table_name="sales_inquiries")
        except Exception:
            pass
    op.drop_table("sales_inquiries")
