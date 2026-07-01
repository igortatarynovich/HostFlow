"""Document reference foundation (M1): canonical types, packs, tenant enablement.

Revision ID: 202608130001_document_reference_foundation
Revises: 202608120003_merge_heads_reminders_and_own_company
Create Date: 2026-08-13 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608130001_document_reference_foundation"
down_revision: RevisionType = "202608120003_merge_heads_reminders_and_own_company"
branch_labels: RevisionType = None
depends_on: RevisionType = None


JSONB = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "ref_document_types",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("public_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("origin", sa.String(length=24), nullable=False, server_default=sa.text("'system'")),
        sa.Column("category_code", sa.String(length=64), nullable=False),
        sa.Column("subcategory_code", sa.String(length=64), nullable=True),
        sa.Column("criticality", sa.String(length=32), nullable=False, server_default=sa.text("'informational'")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_ref_document_types_code"),
    )
    op.create_index("ix_ref_document_types_status", "ref_document_types", ["status"], unique=False)
    op.create_index("ix_ref_document_types_origin", "ref_document_types", ["origin"], unique=False)
    op.create_index("ix_ref_document_types_category", "ref_document_types", ["category_code", "subcategory_code"], unique=False)
    op.create_index("ix_ref_document_types_criticality", "ref_document_types", ["criticality"], unique=False)

    op.create_table(
        "ref_document_type_i18n",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_type_id", sa.String(length=36), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("public_name", sa.String(length=255), nullable=False),
        sa.Column("aliases", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.ForeignKeyConstraint(["document_type_id"], ["ref_document_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_type_id", "locale", name="uq_ref_document_type_i18n_doc_locale"),
    )
    op.create_index("ix_ref_document_type_i18n_document_type_id", "ref_document_type_i18n", ["document_type_id"], unique=False)

    op.create_table(
        "ref_document_type_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_type_id", sa.String(length=36), nullable=False),
        sa.Column("version_code", sa.String(length=64), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("deprecation_reason", sa.Text(), nullable=True),
        sa.Column("replacement_document_type_id", sa.String(length=36), nullable=True),
        sa.Column("schema_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("expiry_rules_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("automation_flags_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("verification_profile_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("stage_applicability_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("position_applicability_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("entity_applicability_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("business_purposes_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status_model", sa.String(length=32), nullable=False, server_default=sa.text("'evidence'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_ref_document_type_versions_valid_range"),
        sa.ForeignKeyConstraint(["document_type_id"], ["ref_document_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["replacement_document_type_id"], ["ref_document_types.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_type_id", "version_code", name="uq_ref_document_type_versions_doc_ver"),
    )
    op.create_index("ix_ref_document_type_versions_document_type_id", "ref_document_type_versions", ["document_type_id"], unique=False)
    op.create_index("ix_ref_document_type_versions_validity", "ref_document_type_versions", ["valid_from", "valid_to"], unique=False)

    op.create_table(
        "ref_document_type_country_applicability",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_type_version_id", sa.String(length=36), nullable=False),
        sa.Column("applicability_scope", sa.String(length=32), nullable=False, server_default=sa.text("'global'")),
        sa.Column("country_codes", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("country_group_codes", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("issuing_country_rules_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("work_country_rules_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("residence_country_rules_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["document_type_version_id"], ["ref_document_type_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ref_document_type_country_app_doc_ver", "ref_document_type_country_applicability", ["document_type_version_id"], unique=False)
    op.create_index("ix_ref_document_type_country_app_scope", "ref_document_type_country_applicability", ["applicability_scope"], unique=False)

    op.create_table(
        "ref_packs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("industry_code", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_ref_packs_code"),
    )
    op.create_index("ix_ref_packs_country_code", "ref_packs", ["country_code"], unique=False)
    op.create_index("ix_ref_packs_industry_code", "ref_packs", ["industry_code"], unique=False)
    op.create_index("ix_ref_packs_status", "ref_packs", ["status"], unique=False)

    op.create_table(
        "ref_pack_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pack_id", sa.String(length=36), nullable=False),
        sa.Column("document_type_version_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(["pack_id"], ["ref_packs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_type_version_id"], ["ref_document_type_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pack_id", "document_type_version_id", name="uq_ref_pack_items_pack_doc_ver"),
    )
    op.create_index("ix_ref_pack_items_pack_id", "ref_pack_items", ["pack_id"], unique=False)
    op.create_index("ix_ref_pack_items_doc_ver_id", "ref_pack_items", ["document_type_version_id"], unique=False)

    op.create_table(
        "ref_pack_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pack_id", sa.String(length=36), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("condition_expr", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("effect_type", sa.String(length=64), nullable=False),
        sa.Column("effect_payload", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["pack_id"], ["ref_packs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ref_pack_rules_pack_id", "ref_pack_rules", ["pack_id"], unique=False)

    op.create_table(
        "tenant_document_pack_enablements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("pack_id", sa.String(length=36), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["ref_packs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "pack_id", name="uq_tenant_document_pack_enablements_tenant_pack"),
    )
    op.create_index("ix_tenant_document_pack_enablements_tenant_id", "tenant_document_pack_enablements", ["tenant_id"], unique=False)
    op.create_index("ix_tenant_document_pack_enablements_pack_id", "tenant_document_pack_enablements", ["pack_id"], unique=False)

    op.create_table(
        "tenant_document_type_overrides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("document_type_id", sa.String(length=36), nullable=False),
        sa.Column("scope_type", sa.String(length=24), nullable=False),
        sa.Column("scope_id", sa.String(length=36), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("required_level", sa.String(length=24), nullable=True),
        sa.Column("alert_days_before_expiry", sa.Integer(), nullable=True),
        sa.Column("responsible_role", sa.String(length=64), nullable=True),
        sa.Column("internal_instruction", sa.Text(), nullable=True),
        sa.Column("client_specific_requirement_json", JSONB, nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.CheckConstraint("(scope_type <> 'tenant') OR (scope_id IS NULL)", name="ck_tenant_doc_type_overrides_scope"),
        sa.ForeignKeyConstraint(["document_type_id"], ["ref_document_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_document_type_overrides_tenant_id", "tenant_document_type_overrides", ["tenant_id"], unique=False)
    op.create_index("ix_tenant_document_type_overrides_document_type_id", "tenant_document_type_overrides", ["document_type_id"], unique=False)

    op.create_table(
        "tenant_document_type_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("requested_code", sa.String(length=128), nullable=False),
        sa.Column("requested_name", sa.String(length=255), nullable=False),
        sa.Column("requested_payload", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'requested'")),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_document_type_requests_tenant_status", "tenant_document_type_requests", ["tenant_id", "status"], unique=False)

    op.add_column("documents", sa.Column("document_type_id", sa.String(length=36), nullable=True))
    op.add_column("documents", sa.Column("document_type_version_id", sa.String(length=36), nullable=True))
    op.create_index("ix_documents_document_type_id", "documents", ["document_type_id"], unique=False)
    op.create_index("ix_documents_document_type_version_id", "documents", ["document_type_version_id"], unique=False)
    op.create_foreign_key("fk_docs_ref_doc_type_id", "documents", "ref_document_types", ["document_type_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_docs_ref_doc_type_ver_id", "documents", "ref_document_type_versions", ["document_type_version_id"], ["id"], ondelete="RESTRICT")

    op.add_column("document_policies", sa.Column("ref_document_type_id", sa.String(length=36), nullable=True))
    op.create_index("ix_document_policies_ref_document_type_id", "document_policies", ["ref_document_type_id"], unique=False)
    op.create_foreign_key(
        "fk_doc_policies_ref_doc_type_id",
        "document_policies",
        "ref_document_types",
        ["ref_document_type_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("document_ruleset_versions", sa.Column("reference_snapshot_version", sa.String(length=64), nullable=True))
    op.add_column("document_ruleset_versions", sa.Column("reference_snapshot_hash", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("document_ruleset_versions", "reference_snapshot_hash")
    op.drop_column("document_ruleset_versions", "reference_snapshot_version")

    op.drop_constraint("fk_doc_policies_ref_doc_type_id", "document_policies", type_="foreignkey")
    op.drop_index("ix_document_policies_ref_document_type_id", table_name="document_policies")
    op.drop_column("document_policies", "ref_document_type_id")

    op.drop_constraint("fk_docs_ref_doc_type_ver_id", "documents", type_="foreignkey")
    op.drop_constraint("fk_docs_ref_doc_type_id", "documents", type_="foreignkey")
    op.drop_index("ix_documents_document_type_version_id", table_name="documents")
    op.drop_index("ix_documents_document_type_id", table_name="documents")
    op.drop_column("documents", "document_type_version_id")
    op.drop_column("documents", "document_type_id")

    op.drop_index("ix_tenant_document_type_requests_tenant_status", table_name="tenant_document_type_requests")
    op.drop_table("tenant_document_type_requests")

    op.drop_index("ix_tenant_document_type_overrides_document_type_id", table_name="tenant_document_type_overrides")
    op.drop_index("ix_tenant_document_type_overrides_tenant_id", table_name="tenant_document_type_overrides")
    op.drop_table("tenant_document_type_overrides")

    op.drop_index("ix_tenant_document_pack_enablements_pack_id", table_name="tenant_document_pack_enablements")
    op.drop_index("ix_tenant_document_pack_enablements_tenant_id", table_name="tenant_document_pack_enablements")
    op.drop_table("tenant_document_pack_enablements")

    op.drop_index("ix_ref_pack_rules_pack_id", table_name="ref_pack_rules")
    op.drop_table("ref_pack_rules")

    op.drop_index("ix_ref_pack_items_doc_ver_id", table_name="ref_pack_items")
    op.drop_index("ix_ref_pack_items_pack_id", table_name="ref_pack_items")
    op.drop_table("ref_pack_items")

    op.drop_index("ix_ref_packs_status", table_name="ref_packs")
    op.drop_index("ix_ref_packs_industry_code", table_name="ref_packs")
    op.drop_index("ix_ref_packs_country_code", table_name="ref_packs")
    op.drop_table("ref_packs")

    op.drop_index("ix_ref_document_type_country_app_scope", table_name="ref_document_type_country_applicability")
    op.drop_index("ix_ref_document_type_country_app_doc_ver", table_name="ref_document_type_country_applicability")
    op.drop_table("ref_document_type_country_applicability")

    op.drop_index("ix_ref_document_type_versions_validity", table_name="ref_document_type_versions")
    op.drop_index("ix_ref_document_type_versions_document_type_id", table_name="ref_document_type_versions")
    op.drop_table("ref_document_type_versions")

    op.drop_index("ix_ref_document_type_i18n_document_type_id", table_name="ref_document_type_i18n")
    op.drop_table("ref_document_type_i18n")

    op.drop_index("ix_ref_document_types_criticality", table_name="ref_document_types")
    op.drop_index("ix_ref_document_types_category", table_name="ref_document_types")
    op.drop_index("ix_ref_document_types_origin", table_name="ref_document_types")
    op.drop_index("ix_ref_document_types_status", table_name="ref_document_types")
    op.drop_table("ref_document_types")
