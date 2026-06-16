"""Field Registry foundation (P1).

Revision ID: 202608180001_field_registry_p1
Revises: 202608170001_migrate_meta_form_routes
Create Date: 2026-08-18 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608180001_field_registry_p1"
down_revision: RevisionType = "202608170001_migrate_meta_form_routes"
branch_labels: RevisionType = None
depends_on: RevisionType = None

JSONB = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql")

_REGISTRY_COLS = [
    sa.Column("id", sa.String(length=36), nullable=False),
    sa.Column("module", sa.String(length=32), nullable=False),
    sa.Column("tenant_id", sa.String(length=36), nullable=False, server_default=sa.text("''")),
    sa.Column("code", sa.String(length=128), nullable=False),
    sa.Column("registry_version", sa.String(length=32), nullable=False, server_default=sa.text("'field_registry_v1'")),
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


def upgrade() -> None:
    op.create_table(
        "fr_canonical_fields",
        *_REGISTRY_COLS,
        sa.Column("qualified_code", sa.String(length=191), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("field_type", sa.String(length=32), nullable=False),
        sa.Column("label_key", sa.String(length=255), nullable=True),
        sa.Column("ownership", sa.String(length=32), nullable=False),
        sa.Column("reference_domain", sa.String(length=64), nullable=True),
        sa.Column("pii_class", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fr_canonical_fields_module", "fr_canonical_fields", ["module"], unique=False)
    op.create_index("ix_fr_canonical_fields_tenant_id", "fr_canonical_fields", ["tenant_id"], unique=False)
    op.create_index("ix_fr_canonical_fields_qualified_code", "fr_canonical_fields", ["qualified_code"], unique=False)
    op.create_index("ix_fr_canonical_fields_entity_type", "fr_canonical_fields", ["entity_type"], unique=False)
    op.create_unique_constraint(
        "uq_fr_canonical_fields_scope_code",
        "fr_canonical_fields",
        ["tenant_id", "qualified_code"],
    )

    op.create_table(
        "fr_card_layout_profiles",
        *_REGISTRY_COLS,
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fr_card_layout_profiles_module", "fr_card_layout_profiles", ["module"], unique=False)
    op.create_index("ix_fr_card_layout_profiles_tenant_id", "fr_card_layout_profiles", ["tenant_id"], unique=False)
    op.create_index("ix_fr_card_layout_profiles_entity_type", "fr_card_layout_profiles", ["entity_type"], unique=False)
    op.create_unique_constraint(
        "uq_fr_card_layout_profiles_scope_code",
        "fr_card_layout_profiles",
        ["tenant_id", "module", "code"],
    )

    op.create_table(
        "fr_card_layout_fields",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("layout_profile_id", sa.String(length=36), nullable=False),
        sa.Column("canonical_field_id", sa.String(length=36), nullable=False),
        sa.Column("section_code", sa.String(length=64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("label_override", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["layout_profile_id"], ["fr_card_layout_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["canonical_field_id"], ["fr_canonical_fields.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fr_card_layout_fields_layout_profile_id",
        "fr_card_layout_fields",
        ["layout_profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_fr_card_layout_fields_canonical_field_id",
        "fr_card_layout_fields",
        ["canonical_field_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_fr_card_layout_fields_layout_field",
        "fr_card_layout_fields",
        ["layout_profile_id", "canonical_field_id"],
    )


def downgrade() -> None:
    op.drop_table("fr_card_layout_fields")
    op.drop_table("fr_card_layout_profiles")
    op.drop_table("fr_canonical_fields")
