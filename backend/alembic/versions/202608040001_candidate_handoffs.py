"""Add candidate_handoffs table for handoff workflow.

Revision ID: 202608040001
Revises: 202608030001_contact_attempts
Create Date: 2026-08-04 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608040001_candidate_handoffs"
down_revision: RevisionType = "202608030001_contact_attempts"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    if not _has_table(conn, "candidate_handoffs"):
        op.create_table(
            "candidate_handoffs",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("candidate_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("agency_tenant_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("client_company_id", sa.String(length=36), nullable=True, index=True),
            sa.Column("client_tenant_id", sa.String(length=36), nullable=True, index=True),
            sa.Column("requested_by_user_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("assigned_to_user_id", sa.String(length=36), nullable=True, index=True),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                index=True,
                comment="pending_review | accepted | rejected | returned | cancelled",
            ),
            sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True, index=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("return_reason", sa.Text(), nullable=True),
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
            sa.ForeignKeyConstraint(
                ["candidate_id"],
                ["candidates.id"],
                name="fk_handoffs_candidate",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["agency_tenant_id"],
                ["tenants.id"],
                name="fk_handoffs_agency",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["client_company_id"],
                ["companies.id"],
                name="fk_handoffs_client_company",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["client_tenant_id"],
                ["tenants.id"],
                name="fk_handoffs_client_tenant",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["requested_by_user_id"],
                ["users.id"],
                name="fk_handoffs_requested_by",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["assigned_to_user_id"],
                ["users.id"],
                name="fk_handoffs_assigned_to",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["reviewed_by_user_id"],
                ["users.id"],
                name="fk_handoffs_reviewed_by",
                ondelete="SET NULL",
            ),
            sa.CheckConstraint(
                "(client_company_id IS NOT NULL AND client_tenant_id IS NULL) "
                "OR (client_company_id IS NULL AND client_tenant_id IS NOT NULL)",
                name="ck_handoffs_client_exactly_one",
            ),
        )
        op.create_index(
            "ix_handoffs_candidate_client_status",
            "candidate_handoffs",
            ["candidate_id", "client_company_id", "status"],
        )
        op.create_index(
            "ix_handoffs_client_pending",
            "candidate_handoffs",
            ["client_company_id", "status"],
            postgresql_where=sa.text("status = 'pending_review'"),
        )
        op.create_index(
            "ix_handoffs_client_tenant_pending",
            "candidate_handoffs",
            ["client_tenant_id", "status"],
            postgresql_where=sa.text("status = 'pending_review' AND client_tenant_id IS NOT NULL"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "candidate_handoffs"):
        op.drop_index("ix_handoffs_client_tenant_pending", table_name="candidate_handoffs")
        op.drop_index("ix_handoffs_client_pending", table_name="candidate_handoffs")
        op.drop_index("ix_handoffs_candidate_client_status", table_name="candidate_handoffs")
        op.drop_table("candidate_handoffs")
