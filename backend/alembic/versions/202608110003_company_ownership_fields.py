"""Add explicit company ownership fields.

Revision ID: 202608110003_company_ownership_fields
Revises: 202608110002
Create Date: 2026-08-11
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202608110003_company_ownership_fields"
down_revision: Union[str, None] = "202608110002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("owner_user_id", sa.String(length=36), nullable=True))
    op.add_column("companies", sa.Column("manager_user_id", sa.String(length=36), nullable=True))
    op.create_index("ix_companies_owner_user_id", "companies", ["owner_user_id"], unique=False)
    op.create_index("ix_companies_manager_user_id", "companies", ["manager_user_id"], unique=False)
    try:
        op.create_foreign_key(
            "fk_companies_owner_user_id_users",
            "companies",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass
    try:
        op.create_foreign_key(
            "fk_companies_manager_user_id_users",
            "companies",
            "users",
            ["manager_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_constraint("fk_companies_manager_user_id_users", "companies", type_="foreignkey")
    except Exception:
        pass
    try:
        op.drop_constraint("fk_companies_owner_user_id_users", "companies", type_="foreignkey")
    except Exception:
        pass
    op.drop_index("ix_companies_manager_user_id", table_name="companies")
    op.drop_index("ix_companies_owner_user_id", table_name="companies")
    op.drop_column("companies", "manager_user_id")
    op.drop_column("companies", "owner_user_id")
