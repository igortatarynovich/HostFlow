"""add scanner tables and drop legacy document_scan_sessions

Revision ID: 202511130001
Revises: 202605200001
Create Date: 2025-11-13 15:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202511130001"
down_revision = "202605200001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Drop legacy table if it exists
    try:
        op.drop_table("document_scan_sessions")
    except Exception:
        pass
    try:
        sa.Enum(name="document_scan_status_enum").drop(bind, checkfirst=True)
    except Exception:
        pass

    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE scan_session_status_enum AS ENUM (
                'in_progress',
                'processing',
                'done',
                'failed',
                'cancelled',
                'expired'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE scan_page_status_enum AS ENUM (
                'pending',
                'uploaded',
                'processing',
                'ok',
                'needs_review',
                'rejected',
                'error'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END$$;
        """
    )

    op.create_table(
        "scan_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("document_type", sa.String(length=128), nullable=False),
        sa.Column("document_kind_id", sa.String(length=36), nullable=True),
        sa.Column("preset_code", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "in_progress",
                "processing",
                "done",
                "failed",
                "cancelled",
                "expired",
                name="scan_session_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="in_progress",
        ),
        sa.Column("expected_pages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("quality_summary", sa.JSON(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_scan_sessions_tenant_id", "scan_sessions", ["tenant_id"])
    op.create_index("ix_scan_sessions_candidate_id", "scan_sessions", ["candidate_id"])

    op.create_table(
        "scan_pages",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("scan_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_code", sa.String(length=64), nullable=False),
        sa.Column("page_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("original_path", sa.String(length=512), nullable=True),
        sa.Column("processed_path", sa.String(length=512), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "uploaded",
                "processing",
                "ok",
                "needs_review",
                "rejected",
                "error",
                name="scan_page_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("rotation", sa.Integer, nullable=False, server_default="0"),
        sa.Column("applied_filter", sa.String(length=32), nullable=True),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("issues", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_scan_pages_session_id", "scan_pages", ["session_id"])


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_scan_pages_session_id", table_name="scan_pages")
    op.drop_table("scan_pages")
    op.drop_index("ix_scan_sessions_candidate_id", table_name="scan_sessions")
    op.drop_index("ix_scan_sessions_tenant_id", table_name="scan_sessions")
    op.drop_table("scan_sessions")
    try:
        sa.Enum(name="scan_page_status_enum").drop(bind, checkfirst=True)
    except Exception:
        pass
    try:
        sa.Enum(name="scan_session_status_enum").drop(bind, checkfirst=True)
    except Exception:
        pass

    document_scan_enum = sa.Enum(
        "pending",
        "in_progress",
        "uploaded",
        "completed",
        "expired",
        "cancelled",
        name="document_scan_status_enum",
    )
    document_scan_enum.create(bind, checkfirst=True)
    op.create_table(
        "document_scan_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column(
            "candidate_id",
            sa.String(length=36),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("doc_type", sa.String(length=100), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("status", document_scan_enum, nullable=False, server_default="pending"),
        sa.Column(
            "document_id",
            sa.String(length=36),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_document_scan_sessions_tenant_id", "document_scan_sessions", ["tenant_id"])
    op.create_index("ix_document_scan_sessions_candidate_id", "document_scan_sessions", ["candidate_id"])
    op.create_index(
        "ix_document_scan_sessions_document_id",
        "document_scan_sessions",
        ["document_id"],
    )
    op.create_index("ix_document_scan_sessions_token", "document_scan_sessions", ["token"], unique=True)
