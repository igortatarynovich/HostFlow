"""communications command audits

Revision ID: 202608100001
Revises: 202608090001
Create Date: 2026-02-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "202608100001"
down_revision: Union[str, None] = "202608090001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "communication_command_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("command_id", sa.String(length=64), nullable=False),
        sa.Column("command_label", sa.String(length=255), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("actions_json", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comm_cmd_audit_tenant_created", "communication_command_audits", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_comm_cmd_audit_tenant_thread", "communication_command_audits", ["tenant_id", "thread_id", "created_at"], unique=False)
    op.create_index("ix_comm_cmd_audit_tenant_actor", "communication_command_audits", ["tenant_id", "actor_user_id", "created_at"], unique=False)
    op.create_index("ix_comm_cmd_audit_tenant_cmd", "communication_command_audits", ["tenant_id", "command_id", "created_at"], unique=False)
    op.create_index("ix_comm_cmd_audit_tenant_channel", "communication_command_audits", ["tenant_id", "channel", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_comm_cmd_audit_tenant_channel", table_name="communication_command_audits")
    op.drop_index("ix_comm_cmd_audit_tenant_cmd", table_name="communication_command_audits")
    op.drop_index("ix_comm_cmd_audit_tenant_actor", table_name="communication_command_audits")
    op.drop_index("ix_comm_cmd_audit_tenant_thread", table_name="communication_command_audits")
    op.drop_index("ix_comm_cmd_audit_tenant_created", table_name="communication_command_audits")
    op.drop_table("communication_command_audits")
