"""Expand reminders for full module and add reminder_events

Revision ID: 202503070900_reminders_full_module
Revises: 00bfe5b21d89_merge_all_heads
Create Date: 2025-03-07 09:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "202503070900_reminders_full_module"
down_revision: Union[str, Sequence[str], None] = "00bfe5b21d89"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "sqlite":
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table});").fetchall()
        return any(row[1] == column for row in rows)
    row = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :t
              AND column_name = :c
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return bool(row)


def upgrade() -> None:
    # Expand reminders table with new fields
    with op.batch_alter_table("reminders", recreate="auto") as batch:
        if not _has_column("reminders", "title"):
            batch.add_column(sa.Column("title", sa.String(length=256), nullable=True))
        if not _has_column("reminders", "description"):
            batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        if not _has_column("reminders", "owner_id"):
            batch.add_column(sa.Column("owner_id", sa.String(length=36), nullable=True))
        if not _has_column("reminders", "assignee_id"):
            batch.add_column(sa.Column("assignee_id", sa.String(length=36), nullable=True))
        if not _has_column("reminders", "priority"):
            batch.add_column(sa.Column("priority", sa.String(length=16), nullable=True))
        if not _has_column("reminders", "channel"):
            batch.add_column(
                sa.Column(
                    "channel",
                    sa.String(length=32),
                    nullable=True,
                    server_default=sa.text("'internal'"),
                )
            )
        if not _has_column("reminders", "remind_at"):
            batch.add_column(sa.Column("remind_at", sa.DateTime(timezone=True), nullable=True))
        if not _has_column("reminders", "snoozed_until"):
            batch.add_column(sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True))
        if not _has_column("reminders", "completed_at"):
            batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        if not _has_column("reminders", "recurrence_json"):
            batch.add_column(sa.Column("recurrence_json", sa.JSON(), nullable=True))

    # New indexes for assignee/due/remind and status/due
    for name, cols in (
        ("ix_reminders_assignee_remind", ["tenant_id", "assignee_id", "remind_at"]),
        ("ix_reminders_assignee_due", ["tenant_id", "assignee_id", "due_at"]),
        ("ix_reminders_status_due", ["tenant_id", "status", "due_at"]),
    ):
        try:
            op.create_index(name, "reminders", cols)
        except Exception:
            # index may already exist if migration reruns
            pass

    # Create reminder_events audit table
    if not _has_table("reminder_events"):
        op.create_table(
            "reminder_events",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("reminder_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index("ix_reminder_events_tenant", "reminder_events", ["tenant_id"])
        op.create_index("ix_reminder_events_reminder", "reminder_events", ["reminder_id"])


def downgrade() -> None:
    # Drop reminder_events
    if _has_table("reminder_events"):
        try:
            op.drop_index("ix_reminder_events_reminder", table_name="reminder_events")
        except Exception:
            pass
        try:
            op.drop_index("ix_reminder_events_tenant", table_name="reminder_events")
        except Exception:
            pass
        op.drop_table("reminder_events")

    # Drop new indexes
    for name in (
        "ix_reminders_assignee_remind",
        "ix_reminders_assignee_due",
        "ix_reminders_status_due",
    ):
        try:
            op.drop_index(name, table_name="reminders")
        except Exception:
            pass

    # Drop added columns
    with op.batch_alter_table("reminders", recreate="auto") as batch:
        for column in (
            "recurrence_json",
            "completed_at",
            "snoozed_until",
            "remind_at",
            "channel",
            "priority",
            "assignee_id",
            "owner_id",
            "description",
            "title",
        ):
            if _has_column("reminders", column):
                batch.drop_column(column)
