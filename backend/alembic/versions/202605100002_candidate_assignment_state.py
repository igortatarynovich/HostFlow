"""candidates.assignment_state — queue vs assigned vs claimed (recruitment CRM).

Revision ID: 202605100002_cas
Revises: 202605100001_ras
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605100002_cas"
down_revision: Union[str, None] = "202605100001_ras"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn: sa.Connection, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    cols = insp.get_columns(table, schema=None)
    return any(c["name"] == column for c in cols)


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "candidates", "assignment_state"):
        op.add_column(
            "candidates",
            sa.Column(
                "assignment_state",
                sa.String(32),
                nullable=False,
                server_default=sa.text("'unassigned'"),
            ),
        )
        op.create_index(
            "ix_candidates_assignment_state",
            "candidates",
            ["assignment_state"],
        )

    # Backfill: recruiter set → assigned (legacy rows treated as routed, not self-claimed).
    op.execute(
        """
        UPDATE candidates
        SET assignment_state = 'assigned'
        WHERE recruiter_id IS NOT NULL AND deleted_at IS NULL
        """
    )
    op.execute(
        """
        UPDATE candidates
        SET assignment_state = 'unassigned'
        WHERE recruiter_id IS NULL AND deleted_at IS NULL
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "candidates", "assignment_state"):
        op.drop_index("ix_candidates_assignment_state", table_name="candidates")
        op.drop_column("candidates", "assignment_state")
