"""Immutable Entity Profile publication versions.

Revision ID: 202610090001_entity_profile_publication_versions
Revises: 202610080001_hr_employment_terms_preparation

ADR-043 Slice 1: introduce immutable Entity Profile revision identity.
Field/document version bindings are intentionally out of scope.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610090001_entity_profile_publication_versions"
down_revision: Union[str, None] = "202610080001_hr_employment_terms_preparation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONB = sa.JSON().with_variant(
    sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
    "postgresql",
)


def upgrade() -> None:
    op.add_column(
        "ep_entity_profiles",
        sa.Column(
            "published_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "ep_entity_profiles",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "ep_entity_profile_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("entity_profile_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("registry_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("module_owner", sa.String(length=32), nullable=False),
        sa.Column("default_layout_code", sa.String(length=128), nullable=True),
        sa.Column("process_profile_code", sa.String(length=128), nullable=True),
        sa.Column("config", JSONB, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_profile_id"],
            ["ep_entity_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "entity_profile_id",
            "version",
            name="uq_ep_entity_profile_versions_scope_profile_ver",
        ),
    )
    op.create_index(
        "ix_ep_entity_profile_versions_entity_profile_id",
        "ep_entity_profile_versions",
        ["entity_profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_ep_entity_profile_versions_scope_profile",
        "ep_entity_profile_versions",
        ["tenant_id", "entity_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ep_entity_profile_versions_scope_profile",
        table_name="ep_entity_profile_versions",
    )
    op.drop_index(
        "ix_ep_entity_profile_versions_entity_profile_id",
        table_name="ep_entity_profile_versions",
    )
    op.drop_table("ep_entity_profile_versions")
    op.drop_column("ep_entity_profiles", "published_at")
    op.drop_column("ep_entity_profiles", "published_version")
