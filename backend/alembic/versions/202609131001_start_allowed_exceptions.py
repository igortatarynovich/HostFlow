"""workforce_start_allowed_exceptions — typed PEM-1 start_allowed exceptions

Revision ID: 202609131001_start_allowed_exceptions
Revises: 202609030001_tenant_document_policy_delta
Create Date: 2026-09-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202609131001_start_allowed_exceptions"
down_revision: Union[str, None] = "202609030001_tenant_document_policy_delta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
    op.create_table(
        "workforce_start_allowed_exceptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "employee_id",
            sa.String(length=36),
            sa.ForeignKey("workforce_employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("handoff_id", sa.String(length=36), nullable=True),
        sa.Column("requirement_code", sa.String(length=128), nullable=False),
        sa.Column("exception_code", sa.String(length=128), nullable=False),
        sa.Column("facts_json", json_type, nullable=False),
        sa.Column("evidence_refs_json", json_type, nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_start_allowed_exc_tenant", "workforce_start_allowed_exceptions", ["tenant_id"])
    op.create_index("ix_start_allowed_exc_employee", "workforce_start_allowed_exceptions", ["employee_id"])
    op.create_index("ix_start_allowed_exc_handoff", "workforce_start_allowed_exceptions", ["handoff_id"])


def downgrade() -> None:
    op.drop_index("ix_start_allowed_exc_handoff", table_name="workforce_start_allowed_exceptions")
    op.drop_index("ix_start_allowed_exc_employee", table_name="workforce_start_allowed_exceptions")
    op.drop_index("ix_start_allowed_exc_tenant", table_name="workforce_start_allowed_exceptions")
    op.drop_table("workforce_start_allowed_exceptions")
