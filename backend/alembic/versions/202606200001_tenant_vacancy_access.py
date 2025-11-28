"""Tenant vacancy access table

Revision ID: 202606200001_tenant_vacancy_access
Revises: 202606150001_tenant_management_phase3
Create Date: 2025-06-20 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

RevisionType = Union[str, Sequence[str], None]

revision: str = "202606200001_tenant_vacancy_access"
down_revision: RevisionType = "202606150001_tenant_management_phase3"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "tenant_vacancy_access",
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tenant_id", "vacancy_id"),
    )
    op.create_index(
        "ix_tenant_vacancy_access_vacancy",
        "tenant_vacancy_access",
        ["vacancy_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_vacancy_access_vacancy", table_name="tenant_vacancy_access")
    op.drop_table("tenant_vacancy_access")
