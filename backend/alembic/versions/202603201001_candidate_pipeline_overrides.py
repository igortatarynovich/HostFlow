"""candidate pipeline document overrides (recruiter request / manager approve)

Revision ID: 202603201001
Revises: 202603181200
Create Date: 2026-03-20
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202603201001"
down_revision: Union[str, Sequence[str], None] = "202603181200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "candidate_pipeline_overrides"):
        return

    op.create_table(
        "candidate_pipeline_overrides",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("candidate_id", sa.String(length=36), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type_code", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_scope", sa.String(length=16), nullable=False, server_default="pipeline"),
        sa.Column("granted_scope", sa.String(length=16), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("requested_by_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_cp_overrides_tenant_candidate",
        "candidate_pipeline_overrides",
        ["tenant_id", "candidate_id"],
    )
    op.create_index(
        "ix_cp_overrides_tenant_candidate_status",
        "candidate_pipeline_overrides",
        ["tenant_id", "candidate_id", "status"],
    )


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "candidate_pipeline_overrides"):
        return
    try:
        op.drop_index("ix_cp_overrides_tenant_candidate_status", table_name="candidate_pipeline_overrides")
    except Exception:
        pass
    try:
        op.drop_index("ix_cp_overrides_tenant_candidate", table_name="candidate_pipeline_overrides")
    except Exception:
        pass
    op.drop_table("candidate_pipeline_overrides")
