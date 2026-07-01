"""Add contact_attempts and final_no_contact_notifications tables.

Revision ID: 202608030001
Revises: 202608020002_merge_heads
Create Date: 2026-08-03 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608030001_contact_attempts"
down_revision: RevisionType = "202608020002_merge_heads"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    if not _has_table(conn, "contact_attempts"):
        op.create_table(
            "contact_attempts",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("candidate_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("attempt_number", sa.Integer(), nullable=False),
            sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("attempted_by_user_id", sa.String(length=36), nullable=True, index=True),
            sa.Column(
                "channel",
                sa.String(length=32),
                nullable=False,
                comment="call | sms | email | whatsapp | messenger",
            ),
            sa.Column(
                "result",
                sa.String(length=32),
                nullable=False,
                comment="no_answer | answered | wrong_number | unavailable",
            ),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["candidate_id"],
                ["candidates.id"],
                name="fk_contact_attempts_candidate",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["attempted_by_user_id"],
                ["users.id"],
                name="fk_contact_attempts_attempted_by",
                ondelete="SET NULL",
            ),
        )
        op.create_index(
            "ix_contact_attempts_candidate_attempt",
            "contact_attempts",
            ["candidate_id", "attempt_number"],
        )

    if not _has_table(conn, "final_no_contact_notifications"):
        op.create_table(
            "final_no_contact_notifications",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("candidate_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("channel", sa.String(length=32), nullable=False),
            sa.Column("template_id", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="sent"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["candidate_id"],
                ["candidates.id"],
                name="fk_final_no_contact_candidate",
                ondelete="CASCADE",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "final_no_contact_notifications"):
        op.drop_table("final_no_contact_notifications")
    if _has_table(conn, "contact_attempts"):
        op.drop_index("ix_contact_attempts_candidate_attempt", table_name="contact_attempts")
        op.drop_table("contact_attempts")
