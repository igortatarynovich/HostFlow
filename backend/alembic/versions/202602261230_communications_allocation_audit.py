"""Add communications allocation audit table.

Revision ID: 202602261230
Revises: 202602261200
Create Date: 2026-02-26
"""

from typing import Sequence, Union

from alembic import op


revision: str = "202602261230"
down_revision: Union[str, Sequence[str], None] = "202602261200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS communication_allocation_audits (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            mode VARCHAR(32) NOT NULL DEFAULT 'allocate',
            channel VARCHAR(32) NOT NULL,
            thread_id VARCHAR(36),
            actor_user_id VARCHAR(36),
            strategy VARCHAR(64),
            assigned BOOLEAN NOT NULL DEFAULT FALSE,
            assignee_id VARCHAR(36),
            reason VARCHAR(255),
            evaluated_at TIMESTAMP WITH TIME ZONE,
            candidates_json JSONB,
            payload JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_alloc_audit_tenant_created ON communication_allocation_audits(tenant_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_alloc_audit_tenant_thread ON communication_allocation_audits(tenant_id, thread_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_alloc_audit_tenant_assignee ON communication_allocation_audits(tenant_id, assignee_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_alloc_audit_tenant_mode ON communication_allocation_audits(tenant_id, mode, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS communication_allocation_audits")

