"""Create candidate_stage_dict table for custom candidate stages

Revision ID: 202607010001_create_candidate_stage_dict
Revises: 202606250004_set_fb_source_for_null_candidates
Create Date: 2026-07-01 00:01:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202607010001_create_candidate_stage_dict"
down_revision: Union[str, None] = "202606250004_set_fb_source_for_null_candidates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create candidate_stage_dict table."""
    op.create_table(
        "candidate_stage_dict",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_stage_tenant_code"),
    )
    # Create index on tenant_id
    op.create_index("ix_candidate_stage_dict_tenant_id", "candidate_stage_dict", ["tenant_id"])


def downgrade() -> None:
    """Drop candidate_stage_dict table."""
    op.drop_index("ix_candidate_stage_dict_tenant_id", table_name="candidate_stage_dict")
    op.drop_table("candidate_stage_dict")
