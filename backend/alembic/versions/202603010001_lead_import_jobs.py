"""Create lead_import_jobs table for CSV imports

Revision ID: 202603010001
Revises: 202602150002
Create Date: 2025-11-15 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202603010001"
down_revision = "202602150002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_import_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("processed_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("success_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_report", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
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
        "ix_lead_import_jobs_tenant_status",
        "lead_import_jobs",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_lead_import_jobs_tenant_creator",
        "lead_import_jobs",
        ["tenant_id", "created_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_lead_import_jobs_tenant_creator", table_name="lead_import_jobs")
    op.drop_index("ix_lead_import_jobs_tenant_status", table_name="lead_import_jobs")
    op.drop_table("lead_import_jobs")
