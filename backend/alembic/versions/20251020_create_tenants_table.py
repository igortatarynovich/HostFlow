"""Create tenants table for multi-tenancy.

Revision ID: 20251020_create_tenants_table
Revises: 20251015_companies_extend_schema
Create Date: 2025-10-20 09:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


RevisionType = Union[str, Sequence[str], None]

revision: str = "20251020_create_tenants_table"
down_revision: RevisionType = "20251015_companies_extend_schema"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _has_table(conn, table_name: str) -> bool:
    inspector = sa.inspect(conn)
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "tenants"):
        return

    settings_type = sa.JSON()
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
        sa.Column("api_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("settings", settings_type, nullable=True),
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
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_index("ix_tenants_api_key", "tenants", ["api_key"], unique=True)


def downgrade() -> None:
    if _has_table(op.get_bind(), "tenants"):
        op.drop_index("ix_tenants_api_key", table_name="tenants")
        op.drop_index("ix_tenants_slug", table_name="tenants")
        op.drop_table("tenants")
