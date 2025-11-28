"""Add candidate status_reason and new stages.

Revision ID: 202603250001_candidate_status_reason
Revises: 202603150001_documents_timeline_fields
Create Date: 2026-03-25 10:00:00.000000
"""

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202603250001_candidate_status_reason"
down_revision: Union[str, Sequence[str], None] = "202603150001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    with op.batch_alter_table("candidates") as batch:
        batch.add_column(sa.Column("status_reason", sa.JSON(), nullable=True))

    conn = op.get_bind()
    if not _table_exists(conn, "stages"):
        return

    stages_table = sa.table(
        "stages",
        sa.column("code", sa.String),
        sa.column("label", sa.String),
        sa.column("sort", sa.Integer),
        sa.column("need_work_permit", sa.Boolean),
        sa.column("need_visa", sa.Boolean),
        sa.column("need_red_paper", sa.Boolean),
        sa.column("is_terminal", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    existing = {
        row[0]
        for row in conn.execute(
            sa.text("SELECT code FROM stages WHERE code IN ('no_answer', 'declined')")
        ).fetchall()
    }

    now_value = datetime.now(timezone.utc)

    if "no_answer" not in existing:
        conn.execute(
            sa.insert(stages_table).values(
                code="no_answer",
                label="Не отвечает",
                sort=15,
                need_work_permit=False,
                need_visa=False,
                need_red_paper=False,
                is_terminal=False,
                created_at=now_value,
                updated_at=None,
            )
        )

    if "declined" not in existing:
        conn.execute(
            sa.insert(stages_table).values(
                code="declined",
                label="Отказался",
                sort=145,
                need_work_permit=False,
                need_visa=False,
                need_red_paper=False,
                is_terminal=True,
                created_at=now_value,
                updated_at=None,
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "stages"):
        conn.execute(sa.text("DELETE FROM stages WHERE code IN ('no_answer', 'declined')"))

    with op.batch_alter_table("candidates") as batch:
        batch.drop_column("status_reason")
