"""Module Registry foundation (P1).

Revision ID: 202608190001_module_registry_p1
Revises: 202608180001_field_registry_p1
Create Date: 2026-08-19 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608190001_module_registry_p1"
down_revision: RevisionType = "202608180001_field_registry_p1"
branch_labels: RevisionType = None
depends_on: RevisionType = None

JSONB = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql")

_TIMESTAMPS = [
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
]


def upgrade() -> None:
    op.create_table(
        "module_registry",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("module_code", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("owner", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'registered'")),
        sa.Column("registry_version", sa.String(length=32), nullable=False, server_default=sa.text("'module_registry_v1'")),
        sa.Column("manifest", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_TIMESTAMPS,
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module_code", name="uq_module_registry_module_code"),
    )
    op.create_index("ix_module_registry_module_code", "module_registry", ["module_code"], unique=False)
    op.create_index("ix_module_registry_kind", "module_registry", ["kind"], unique=False)
    op.create_index("ix_module_registry_status", "module_registry", ["status"], unique=False)

    op.create_table(
        "tenant_module_installations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("module_code", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False, server_default=sa.text("'enabled'")),
        sa.Column("source", sa.String(length=32), nullable=False, server_default=sa.text("'migration'")),
        sa.Column("settings_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", JSONB, nullable=False, server_default=sa.text("'{}'")),
        *_TIMESTAMPS,
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "module_code", name="uq_tenant_module_installations_scope"),
    )
    op.create_index("ix_tenant_module_installations_tenant_id", "tenant_module_installations", ["tenant_id"], unique=False)
    op.create_index("ix_tenant_module_installations_module_code", "tenant_module_installations", ["module_code"], unique=False)
    op.create_index("ix_tenant_module_installations_state", "tenant_module_installations", ["state"], unique=False)

    op.create_table(
        "module_capabilities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("module_code", sa.String(length=64), nullable=False),
        sa.Column("capability_code", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        *_TIMESTAMPS,
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module_code", "capability_code", name="uq_module_capabilities_module_code"),
    )
    op.create_index("ix_module_capabilities_module_code", "module_capabilities", ["module_code"], unique=False)
    op.create_index("ix_module_capabilities_capability_code", "module_capabilities", ["capability_code"], unique=False)

    op.create_table(
        "module_dependencies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("module_code", sa.String(length=64), nullable=False),
        sa.Column("dependency_module_code", sa.String(length=64), nullable=False),
        sa.Column("dependency_kind", sa.String(length=32), nullable=False),
        sa.Column("capability_code", sa.String(length=128), nullable=True),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        *_TIMESTAMPS,
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "module_code",
            "dependency_module_code",
            "dependency_kind",
            name="uq_module_dependencies_module_dependency_kind",
        ),
    )
    op.create_index("ix_module_dependencies_module_code", "module_dependencies", ["module_code"], unique=False)
    op.create_index("ix_module_dependencies_dependency_module_code", "module_dependencies", ["dependency_module_code"], unique=False)


def downgrade() -> None:
    op.drop_table("module_dependencies")
    op.drop_table("module_capabilities")
    op.drop_table("tenant_module_installations")
    op.drop_table("module_registry")
