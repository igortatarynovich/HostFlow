"""Add candidate_assignee_history table (Phase 2.6.G-5 Stage C).

Append-only audit trail for ``Candidate.recruiter_id`` reassignments.
See ``docs/specs/manager-assignment.md`` §2.5 for the full spec.

Revision ID: 202604190001_candidate_assignee_history
Revises: 202604031200_vac_status_canon
Create Date: 2026-04-19 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202604190001_candidate_assignee_history"
down_revision = "202604031200_vac_status_canon"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_assignee_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("from_user_id", sa.String(length=36), nullable=True),
        sa.Column("to_user_id", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column(
            "actor_kind",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'user'"),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="fk_candidate_assignee_history_candidate",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["from_user_id"],
            ["users.id"],
            name="fk_candidate_assignee_history_from_user",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["to_user_id"],
            ["users.id"],
            name="fk_candidate_assignee_history_to_user",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_candidate_assignee_history_actor",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_candidate_assignee_history_tenant_id",
        "candidate_assignee_history",
        ["tenant_id"],
    )
    op.create_index(
        "ix_candidate_assignee_history_candidate_id",
        "candidate_assignee_history",
        ["candidate_id"],
    )
    op.create_index(
        "ix_candidate_assignee_history_changed_at",
        "candidate_assignee_history",
        ["changed_at"],
    )
    op.create_index(
        "ix_candidate_assignee_history_tenant_candidate",
        "candidate_assignee_history",
        ["tenant_id", "candidate_id"],
    )
    op.create_index(
        "ix_candidate_assignee_history_tenant_changed",
        "candidate_assignee_history",
        ["tenant_id", "changed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_assignee_history_tenant_changed",
        table_name="candidate_assignee_history",
    )
    op.drop_index(
        "ix_candidate_assignee_history_tenant_candidate",
        table_name="candidate_assignee_history",
    )
    op.drop_index(
        "ix_candidate_assignee_history_changed_at",
        table_name="candidate_assignee_history",
    )
    op.drop_index(
        "ix_candidate_assignee_history_candidate_id",
        table_name="candidate_assignee_history",
    )
    op.drop_index(
        "ix_candidate_assignee_history_tenant_id",
        table_name="candidate_assignee_history",
    )
    op.drop_table("candidate_assignee_history")
