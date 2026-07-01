"""Tenant requirement overrides table (P3B).

Revision ID: 202608230001_requirement_rules_tenant_overrides_p3b
Revises: 202608220004
Create Date: 2026-06-23 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608230001_requirement_rules_tenant_overrides_p3b"
down_revision: RevisionType = "202608220004_entity_profile_p9"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "tenant_requirement_overrides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("entity_profile_code", sa.String(length=128), nullable=True),
        sa.Column("context", sa.String(length=32), nullable=True),
        sa.Column("stage_code", sa.String(length=128), nullable=True),
        sa.Column("override_kind", sa.String(length=16), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("target_code", sa.String(length=191), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'active'")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("approved_by_user_id", sa.String(length=36), nullable=True),
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
    op.create_index(
        "ix_tenant_requirement_overrides_tenant_id",
        "tenant_requirement_overrides",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_tenant_requirement_overrides_target_code",
        "tenant_requirement_overrides",
        ["target_code"],
        unique=False,
    )
    op.create_index(
        "ix_tenant_requirement_overrides_status",
        "tenant_requirement_overrides",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_requirement_overrides_status", table_name="tenant_requirement_overrides")
    op.drop_index("ix_tenant_requirement_overrides_target_code", table_name="tenant_requirement_overrides")
    op.drop_index("ix_tenant_requirement_overrides_tenant_id", table_name="tenant_requirement_overrides")
    op.drop_table("tenant_requirement_overrides")
