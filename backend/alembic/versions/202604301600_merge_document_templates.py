"""Merge document templates + generation logs (placeholders -> candidate documents)

Revision ID: 202604301600_merge_doc_tpl
Revises: 202604301500_workforce_hr_profiles
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202604301600_merge_doc_tpl"
down_revision: Union[str, None] = "202604301500_workforce_hr_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _rls_tenant(table: str) -> None:
    if not _is_postgres():
        return
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = '{table}'
                AND policyname = 'rls_{table}_tenant'
            ) THEN
                CREATE POLICY rls_{table}_tenant ON {table}
                USING (tenant_id::uuid = current_setting('app.tenant_id')::uuid);
            END IF;
        END $$;
    """
    )


def upgrade() -> None:
    jtype = sa.JSON()
    if _is_postgres():
        jtype = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    c_u = sa.TIMESTAMP(timezone=True)
    uid = sa.String(36)

    op.create_table(
        "merge_document_templates",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            uid,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "own_company_id",
            uid,
            sa.ForeignKey("own_companies.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column(
            "output_mime",
            sa.String(128),
            nullable=False,
            server_default="text/plain",
        ),
        sa.Column("variable_bindings", jtype, nullable=True),
        sa.Column("output_filename_pattern", sa.String(512), nullable=True),
        sa.Column(
            "doc_type",
            sa.String(128),
            nullable=False,
            server_default="additional_document",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_merge_document_templates_tenant_company_active",
        "merge_document_templates",
        ["tenant_id", "own_company_id", "is_active"],
    )

    # Partial unique: global templates (own_company_id IS NULL)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_merge_doc_tpl_tenant_global_code
        ON merge_document_templates (tenant_id, code)
        WHERE own_company_id IS NULL;
        """
    )
    # Per-own-company templates
    op.execute(
        """
        CREATE UNIQUE INDEX uq_merge_doc_tpl_tenant_oc_code
        ON merge_document_templates (tenant_id, own_company_id, code)
        WHERE own_company_id IS NOT NULL;
        """
    )

    op.create_table(
        "merge_document_generation_logs",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            uid,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "template_id",
            uid,
            sa.ForeignKey("merge_document_templates.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "candidate_id",
            uid,
            sa.ForeignKey("candidates.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "workforce_employee_id",
            uid,
            sa.ForeignKey("workforce_employees.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "document_id",
            uid,
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("triggered_by_user_id", uid, nullable=True, index=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("context_snapshot", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_merge_doc_gen_logs_tenant_created",
        "merge_document_generation_logs",
        ["tenant_id", "created_at"],
    )

    _rls_tenant("merge_document_templates")
    _rls_tenant("merge_document_generation_logs")


def downgrade() -> None:
    op.drop_index("ix_merge_doc_gen_logs_tenant_created", table_name="merge_document_generation_logs")
    op.drop_table("merge_document_generation_logs")
    op.execute("DROP INDEX IF EXISTS uq_merge_doc_tpl_tenant_oc_code;")
    op.execute("DROP INDEX IF EXISTS uq_merge_doc_tpl_tenant_global_code;")
    op.drop_index("ix_merge_document_templates_tenant_company_active", table_name="merge_document_templates")
    op.drop_table("merge_document_templates")
