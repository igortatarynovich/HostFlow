"""Process Engine registry foundation (P1).

Revision ID: 202608140001_process_engine_registry_p1
Revises: 202608130005_merge_m5_heads
Create Date: 2026-08-14 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608140001_process_engine_registry_p1"
down_revision: RevisionType = "202608130005_merge_m5_heads"
branch_labels: RevisionType = None
depends_on: RevisionType = None

JSONB = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql")

_REGISTRY_COLS = [
    sa.Column("id", sa.String(length=36), nullable=False),
    sa.Column("module", sa.String(length=32), nullable=False),
    sa.Column("tenant_id", sa.String(length=36), nullable=False, server_default=sa.text("''")),
    sa.Column("code", sa.String(length=64), nullable=False),
    sa.Column("registry_version", sa.String(length=32), nullable=False, server_default=sa.text("'process_engine_v1'")),
    sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'active'")),
    sa.Column("name", sa.String(length=255), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
    sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
]


def _registry_table(name: str, *extra: sa.Column) -> None:
    op.create_table(name, *_REGISTRY_COLS, *extra, sa.PrimaryKeyConstraint("id"))
    op.create_index(f"ix_{name}_module", name, ["module"], unique=False)
    op.create_index(f"ix_{name}_tenant_id", name, ["tenant_id"], unique=False)
    op.create_unique_constraint(f"uq_{name}_scope_code", name, ["tenant_id", "module", "code"])


def upgrade() -> None:
    _registry_table(
        "pe_system_stages",
        sa.Column("template_code", sa.String(length=64), nullable=True),
        sa.Column("terminal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("analytics_bucket", sa.String(length=32), nullable=True),
    )
    _registry_table("pe_stage_templates")

    op.create_table(
        "pe_pipeline_templates",
        *_REGISTRY_COLS,
        sa.Column("legacy_funnel_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["legacy_funnel_id"], ["funnels.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pe_pipeline_templates_module", "pe_pipeline_templates", ["module"], unique=False)
    op.create_index("ix_pe_pipeline_templates_tenant_id", "pe_pipeline_templates", ["tenant_id"], unique=False)
    op.create_index("ix_pe_pipeline_templates_legacy_funnel_id", "pe_pipeline_templates", ["legacy_funnel_id"], unique=False)
    op.create_unique_constraint(
        "uq_pe_pipeline_templates_scope_code",
        "pe_pipeline_templates",
        ["tenant_id", "module", "code"],
    )

    op.create_table(
        "pe_process_profiles",
        *_REGISTRY_COLS,
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("pipeline_template_id", sa.String(length=36), nullable=True),
        sa.Column("owner_company_id", sa.String(length=36), nullable=True),
        sa.Column("legacy_candidate_profile_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["pipeline_template_id"], ["pe_pipeline_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["legacy_candidate_profile_id"], ["candidate_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pe_process_profiles_module", "pe_process_profiles", ["module"], unique=False)
    op.create_index("ix_pe_process_profiles_tenant_id", "pe_process_profiles", ["tenant_id"], unique=False)
    op.create_index("ix_pe_process_profiles_pipeline_template_id", "pe_process_profiles", ["pipeline_template_id"], unique=False)
    op.create_index("ix_pe_process_profiles_owner_company_id", "pe_process_profiles", ["owner_company_id"], unique=False)
    op.create_index(
        "ix_pe_process_profiles_legacy_candidate_profile_id",
        "pe_process_profiles",
        ["legacy_candidate_profile_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_pe_process_profiles_scope_code",
        "pe_process_profiles",
        ["tenant_id", "module", "code"],
    )

    op.create_table(
        "pe_transition_rules",
        *_REGISTRY_COLS,
        sa.Column("process_profile_id", sa.String(length=36), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.ForeignKeyConstraint(["process_profile_id"], ["pe_process_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pe_transition_rules_module", "pe_transition_rules", ["module"], unique=False)
    op.create_index("ix_pe_transition_rules_tenant_id", "pe_transition_rules", ["tenant_id"], unique=False)
    op.create_index("ix_pe_transition_rules_process_profile_id", "pe_transition_rules", ["process_profile_id"], unique=False)
    op.create_unique_constraint(
        "uq_pe_transition_rules_scope_code",
        "pe_transition_rules",
        ["tenant_id", "module", "code"],
    )

    op.create_table(
        "pe_handoff_rules",
        *_REGISTRY_COLS,
        sa.Column("handoff_mode", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pe_handoff_rules_module", "pe_handoff_rules", ["module"], unique=False)
    op.create_index("ix_pe_handoff_rules_tenant_id", "pe_handoff_rules", ["tenant_id"], unique=False)
    op.create_unique_constraint(
        "uq_pe_handoff_rules_scope_code",
        "pe_handoff_rules",
        ["tenant_id", "module", "code"],
    )

    op.create_table(
        "pe_field_requirements",
        *_REGISTRY_COLS,
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pe_field_requirements_module", "pe_field_requirements", ["module"], unique=False)
    op.create_index("ix_pe_field_requirements_tenant_id", "pe_field_requirements", ["tenant_id"], unique=False)
    op.create_unique_constraint(
        "uq_pe_field_requirements_scope_code",
        "pe_field_requirements",
        ["tenant_id", "module", "code"],
    )

    op.create_table(
        "pe_document_requirements",
        *_REGISTRY_COLS,
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pe_document_requirements_module", "pe_document_requirements", ["module"], unique=False)
    op.create_index("ix_pe_document_requirements_tenant_id", "pe_document_requirements", ["tenant_id"], unique=False)
    op.create_unique_constraint(
        "uq_pe_document_requirements_scope_code",
        "pe_document_requirements",
        ["tenant_id", "module", "code"],
    )

    op.create_table(
        "pe_override_rules",
        *_REGISTRY_COLS,
        sa.Column("scope", sa.String(length=16), nullable=False, server_default=sa.text("'both'")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pe_override_rules_module", "pe_override_rules", ["module"], unique=False)
    op.create_index("ix_pe_override_rules_tenant_id", "pe_override_rules", ["tenant_id"], unique=False)
    op.create_unique_constraint(
        "uq_pe_override_rules_scope_code",
        "pe_override_rules",
        ["tenant_id", "module", "code"],
    )

    op.add_column(
        "candidate_profiles",
        sa.Column("pe_process_profile_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_candidate_profiles_pe_process_profile_id",
        "candidate_profiles",
        "pe_process_profiles",
        ["pe_process_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_candidate_profiles_pe_process_profile_id",
        "candidate_profiles",
        ["pe_process_profile_id"],
        unique=False,
    )

    op.add_column("funnel_stages", sa.Column("pe_maps_to_module", sa.String(length=32), nullable=True))
    op.add_column("funnel_stages", sa.Column("pe_maps_to_code", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("funnel_stages", "pe_maps_to_code")
    op.drop_column("funnel_stages", "pe_maps_to_module")

    op.drop_index("ix_candidate_profiles_pe_process_profile_id", table_name="candidate_profiles")
    op.drop_constraint("fk_candidate_profiles_pe_process_profile_id", "candidate_profiles", type_="foreignkey")
    op.drop_column("candidate_profiles", "pe_process_profile_id")

    for table in (
        "pe_override_rules",
        "pe_document_requirements",
        "pe_field_requirements",
        "pe_handoff_rules",
        "pe_transition_rules",
        "pe_process_profiles",
        "pe_pipeline_templates",
        "pe_stage_templates",
        "pe_system_stages",
    ):
        op.drop_table(table)
