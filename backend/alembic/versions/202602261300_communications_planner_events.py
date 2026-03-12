"""communications planner events

Revision ID: 202602261300
Revises: 202602261230
Create Date: 2026-02-26 13:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202602261300"
down_revision = "202602261230"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "communication_planner_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="task"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="planned"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("owner_id", sa.String(length=36), nullable=True),
        sa.Column("assignee_id", sa.String(length=36), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("linked_candidate_id", sa.String(length=36), nullable=True),
        sa.Column("linked_company_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comm_planner_tenant_start", "communication_planner_events", ["tenant_id", "start_at"], unique=False)
    op.create_index("ix_comm_planner_tenant_assignee", "communication_planner_events", ["tenant_id", "assignee_id", "start_at"], unique=False)
    op.create_index("ix_comm_planner_tenant_status", "communication_planner_events", ["tenant_id", "status", "start_at"], unique=False)
    op.create_index("ix_comm_planner_tenant_entity", "communication_planner_events", ["tenant_id", "entity_type", "entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_comm_planner_tenant_entity", table_name="communication_planner_events")
    op.drop_index("ix_comm_planner_tenant_status", table_name="communication_planner_events")
    op.drop_index("ix_comm_planner_tenant_assignee", table_name="communication_planner_events")
    op.drop_index("ix_comm_planner_tenant_start", table_name="communication_planner_events")
    op.drop_table("communication_planner_events")
