"""Entity Profile Definition Registry foundation (P1).

Revision ID: 202608220001_entity_profile_p1
Revises: 202608200003
Create Date: 2026-06-22 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608220001_entity_profile_p1"
down_revision: RevisionType = "202608200003"
branch_labels: RevisionType = None
depends_on: RevisionType = None

JSONB = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "ep_entity_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False, server_default=sa.text("''")),
        sa.Column("profile_code", sa.String(length=128), nullable=False),
        sa.Column("registry_version", sa.String(length=32), nullable=False, server_default=sa.text("'entity_profile_v1'")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'active'")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("module_owner", sa.String(length=32), nullable=False),
        sa.Column("default_layout_code", sa.String(length=128), nullable=True),
        sa.Column("document_pack_code", sa.String(length=128), nullable=True),
        sa.Column("process_profile_code", sa.String(length=128), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ep_entity_profiles_tenant_id", "ep_entity_profiles", ["tenant_id"], unique=False)
    op.create_index("ix_ep_entity_profiles_profile_code", "ep_entity_profiles", ["profile_code"], unique=False)
    op.create_index("ix_ep_entity_profiles_entity_type", "ep_entity_profiles", ["entity_type"], unique=False)
    op.create_index("ix_ep_entity_profiles_module_owner", "ep_entity_profiles", ["module_owner"], unique=False)
    op.create_unique_constraint(
        "uq_ep_entity_profiles_scope_code",
        "ep_entity_profiles",
        ["tenant_id", "profile_code"],
    )

    op.create_table(
        "ep_entity_profile_fields",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_profile_id", sa.String(length=36), nullable=False),
        sa.Column("qualified_code", sa.String(length=191), nullable=False),
        sa.Column("canonical_field_id", sa.String(length=36), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("intake_level", sa.String(length=16), nullable=False, server_default=sa.text("'optional'")),
        sa.Column("card_save_level", sa.String(length=16), nullable=False, server_default=sa.text("'optional'")),
        sa.Column("transition_level", sa.String(length=16), nullable=False, server_default=sa.text("'optional'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.ForeignKeyConstraint(["entity_profile_id"], ["ep_entity_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["canonical_field_id"], ["fr_canonical_fields.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ep_entity_profile_fields_entity_profile_id",
        "ep_entity_profile_fields",
        ["entity_profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_ep_entity_profile_fields_qualified_code",
        "ep_entity_profile_fields",
        ["qualified_code"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_ep_entity_profile_fields_profile_code",
        "ep_entity_profile_fields",
        ["entity_profile_id", "qualified_code"],
    )

    op.create_table(
        "ep_intake_presentations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False, server_default=sa.text("''")),
        sa.Column("entity_profile_id", sa.String(length=36), nullable=False),
        sa.Column("intake_source_binding_id", sa.String(length=36), nullable=True),
        sa.Column("presentation_code", sa.String(length=128), nullable=False),
        sa.Column("field_subset", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("presentation_overrides", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.ForeignKeyConstraint(["entity_profile_id"], ["ep_entity_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ep_intake_presentations_tenant_id", "ep_intake_presentations", ["tenant_id"], unique=False)
    op.create_index(
        "ix_ep_intake_presentations_entity_profile_id",
        "ep_intake_presentations",
        ["entity_profile_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_ep_intake_presentations_scope_code",
        "ep_intake_presentations",
        ["tenant_id", "presentation_code"],
    )


def downgrade() -> None:
    op.drop_table("ep_intake_presentations")
    op.drop_table("ep_entity_profile_fields")
    op.drop_table("ep_entity_profiles")
