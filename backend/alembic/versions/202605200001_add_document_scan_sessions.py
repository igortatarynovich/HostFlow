"""add document_scan_sessions table

Revision ID: 202605200001
Revises: 202605050001
Create Date: 2025-05-20 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202605200001"
down_revision = "202605050001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    scan_status_enum = sa.Enum(
        "pending",
        "in_progress",
        "uploaded",
        "completed",
        "expired",
        "cancelled",
        name="document_scan_status_enum",
    )
    scan_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "document_scan_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(length=100), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False, unique=True),
        sa.Column("status", scan_status_enum, nullable=False, server_default="pending"),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_document_scan_sessions_tenant_id", "document_scan_sessions", ["tenant_id"])
    op.create_index("ix_document_scan_sessions_candidate_id", "document_scan_sessions", ["candidate_id"])
    op.create_index("ix_document_scan_sessions_document_id", "document_scan_sessions", ["document_id"])
    op.create_index("ix_document_scan_sessions_token", "document_scan_sessions", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_document_scan_sessions_token", table_name="document_scan_sessions")
    op.drop_index("ix_document_scan_sessions_document_id", table_name="document_scan_sessions")
    op.drop_index("ix_document_scan_sessions_candidate_id", table_name="document_scan_sessions")
    op.drop_index("ix_document_scan_sessions_tenant_id", table_name="document_scan_sessions")
    op.drop_table("document_scan_sessions")
    sa.Enum(name="document_scan_status_enum").drop(op.get_bind(), checkfirst=True)
