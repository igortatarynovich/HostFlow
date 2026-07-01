"""Add tenant limits, usage tracking, document policies and custom fields.

Revision ID: 202501010000_add_tenant_limits_and_document_policies
Revises: 202503070900_reminders_full_module
Create Date: 2025-01-01 00:00:01.000000

This migration adds:
- New limit fields to tenant_licenses (max_candidates_active, max_vacancies_active, max_documents, max_public_portal_links)
- tenant_usage table for tracking usage metrics
- document_policies table for tenant/client/vacancy-level document requirements
- custom_field_definitions and custom_field_values tables for custom fields
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "202501010000_add_tenant_limits_and_document_policies"
down_revision: Union[str, None] = "202503070900_reminders_full_module"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    """Check if we're using PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def _has_column(table: str, column: str) -> bool:
    """Check if column exists in table."""
    if not _is_postgres():
        return False
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = :table_name 
                AND column_name = :column_name
            )
        """
        ),
        {"table_name": table, "column_name": column},
    )
    return bool(result.scalar())


def _has_table(table: str) -> bool:
    """Check if table exists (not a view)."""
    if not _is_postgres():
        return False
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = :table_name
                AND table_type = 'BASE TABLE'
            )
        """
        ),
        {"table_name": table},
    )
    return bool(result.scalar())


def _is_view(table: str) -> bool:
    """Check if object exists as a view."""
    if not _is_postgres():
        return False
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.views 
                WHERE table_name = :table_name
            )
        """
        ),
        {"table_name": table},
    )
    return bool(result.scalar())


def upgrade() -> None:
    """Add tenant limits, usage tracking, document policies and custom fields."""
    if not _is_postgres():
        # SQLite doesn't support all features, skip for now
        return

    # 1. Add new limit fields to tenant_licenses
    if _has_table("tenant_licenses"):
        if not _has_column("tenant_licenses", "max_candidates_active"):
            op.add_column(
                "tenant_licenses",
                sa.Column("max_candidates_active", sa.Integer(), nullable=False, server_default="0"),
            )
        if not _has_column("tenant_licenses", "max_vacancies_active"):
            op.add_column(
                "tenant_licenses",
                sa.Column("max_vacancies_active", sa.Integer(), nullable=False, server_default="0"),
            )
        if not _has_column("tenant_licenses", "max_documents"):
            op.add_column(
                "tenant_licenses",
                sa.Column("max_documents", sa.Integer(), nullable=False, server_default="0"),
            )
        if not _has_column("tenant_licenses", "max_public_portal_links"):
            op.add_column(
                "tenant_licenses",
                sa.Column("max_public_portal_links", sa.Integer(), nullable=False, server_default="0"),
            )

    # 2. Create tenant_usage table (drop view if exists)
    if _is_view("tenant_usage"):
        op.execute("DROP VIEW IF EXISTS tenant_usage CASCADE;")
    if not _has_table("tenant_usage"):
        op.create_table(
            "tenant_usage",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
            sa.Column("metric", sa.String(64), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("tenant_id", "metric", "period_start", "period_end", name="uq_tenant_usage_period"),
        )
        op.create_index("idx_tenant_usage_tenant_metric", "tenant_usage", ["tenant_id", "metric"])
        op.create_index("idx_tenant_usage_period", "tenant_usage", ["period_start", "period_end"])

    # 3. Create document_policies table
    if not _has_table("document_policies"):
        op.create_table(
            "document_policies",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
            sa.Column(
                "scope",
                sa.String(16),
                nullable=False,
            ),  # tenant/client/vacancy
            sa.Column("scope_id", sa.String(36), nullable=True, index=True),
            sa.Column("document_type_id", sa.String(36), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("required", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("alert_days_before_expiry", sa.Integer(), nullable=True),
            sa.Column("owner_user_id", sa.String(36), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "tenant_id", "scope", "scope_id", "document_type_id", name="uq_document_policy_scope"
            ),
        )
        op.create_index("idx_document_policies_tenant_scope", "document_policies", ["tenant_id", "scope", "scope_id"])
        op.create_index("idx_document_policies_doc_type", "document_policies", ["document_type_id"])

    # 4. Create custom_field_definitions table
    if not _has_table("custom_field_definitions"):
        op.create_table(
            "custom_field_definitions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
            sa.Column("scope", sa.String(16), nullable=False),  # candidate/document
            sa.Column("document_type_id", sa.String(36), nullable=True),
            sa.Column("key", sa.String(128), nullable=False),
            sa.Column("label", sa.String(256), nullable=False),
            sa.Column("field_type", sa.String(16), nullable=False),  # text/textarea/number/date/checkbox/select/multiselect
            sa.Column("required", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("options", postgresql.JSONB(), nullable=True),  # для select/multiselect
            sa.Column("help_text", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], ondelete="CASCADE"),
        )
        # Unique constraint зависит от scope: для CANDIDATE (tenant_id, scope, key), для DOCUMENT (tenant_id, scope, document_type_id, key)
        # Создаём через raw SQL для условной уникальности
        op.execute(
            """
            CREATE UNIQUE INDEX uq_custom_field_def_candidate 
            ON custom_field_definitions (tenant_id, scope, key) 
            WHERE scope = 'candidate' AND document_type_id IS NULL;
        """
        )
        op.execute(
            """
            CREATE UNIQUE INDEX uq_custom_field_def_document 
            ON custom_field_definitions (tenant_id, scope, document_type_id, key) 
            WHERE scope = 'document' AND document_type_id IS NOT NULL;
        """
        )
        op.create_index("idx_custom_field_def_tenant_scope", "custom_field_definitions", ["tenant_id", "scope"])
        op.create_index("idx_custom_field_def_doc_type", "custom_field_definitions", ["document_type_id"])

    # 5. Create custom_field_values table
    if not _has_table("custom_field_values"):
        op.create_table(
            "custom_field_values",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
            sa.Column("definition_id", sa.String(36), nullable=False),
            sa.Column("entity_type", sa.String(16), nullable=False),  # candidate/candidate_document
            sa.Column("entity_id", sa.String(36), nullable=False),
            sa.Column("value", postgresql.JSONB(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_by_user_id", sa.String(36), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["definition_id"], ["custom_field_definitions.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "tenant_id", "definition_id", "entity_type", "entity_id", name="uq_custom_field_value_entity"
            ),
        )
        op.create_index("idx_custom_field_values_definition", "custom_field_values", ["definition_id"])
        op.create_index("idx_custom_field_values_entity", "custom_field_values", ["entity_type", "entity_id"])

    # 6. Enable RLS for new tables (only if they are actual tables, not views)
    for table in ["tenant_usage", "document_policies", "custom_field_definitions", "custom_field_values"]:
        if _has_table(table) and not _is_view(table):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
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


def downgrade() -> None:
    """Remove tenant limits, usage tracking, document policies and custom fields."""
    if not _is_postgres():
        return

    # Drop RLS policies
    for table in ["custom_field_values", "custom_field_definitions", "document_policies", "tenant_usage"]:
        if _has_table(table):
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
            op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table};")

    # Drop tables in reverse order
    if _has_table("custom_field_values"):
        op.drop_table("custom_field_values")
    if _has_table("custom_field_definitions"):
        op.drop_index("uq_custom_field_def_document", table_name="custom_field_definitions")
        op.drop_index("uq_custom_field_def_candidate", table_name="custom_field_definitions")
        op.drop_table("custom_field_definitions")
    if _has_table("document_policies"):
        op.drop_table("document_policies")
    if _has_table("tenant_usage"):
        op.drop_table("tenant_usage")

    # Remove columns from tenant_licenses
    if _has_table("tenant_licenses"):
        if _has_column("tenant_licenses", "max_public_portal_links"):
            op.drop_column("tenant_licenses", "max_public_portal_links")
        if _has_column("tenant_licenses", "max_documents"):
            op.drop_column("tenant_licenses", "max_documents")
        if _has_column("tenant_licenses", "max_vacancies_active"):
            op.drop_column("tenant_licenses", "max_vacancies_active")
        if _has_column("tenant_licenses", "max_candidates_active"):
            op.drop_column("tenant_licenses", "max_candidates_active")

