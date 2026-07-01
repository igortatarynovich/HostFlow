"""Create communications core tables (threads, messages, accounts, time-off requests).

Revision ID: 202602261200
Revises: 202602081003, 202602081010, 202602100900
Create Date: 2026-02-26
"""

from typing import Sequence, Union

from alembic import op


revision: str = "202602261200"
down_revision: Union[str, Sequence[str], None] = ("202602081003", "202602081010", "202602100900")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS communication_threads (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            channel VARCHAR(32) NOT NULL,
            channel_account_id VARCHAR(36),
            channel_thread_ref VARCHAR(255),
            subject VARCHAR(512),
            status VARCHAR(32) NOT NULL DEFAULT 'open',
            direction_hint VARCHAR(16),
            entity_type VARCHAR(64),
            entity_id VARCHAR(120),
            linked_company_id VARCHAR(36),
            linked_candidate_id VARCHAR(36),
            owner_id VARCHAR(36),
            assignee_id VARCHAR(36),
            queue_assigned_by VARCHAR(32),
            priority VARCHAR(16) NOT NULL DEFAULT 'normal',
            sla_due_at TIMESTAMP WITH TIME ZONE,
            participants_json JSONB,
            tags_json JSONB,
            thread_meta JSONB,
            last_message_at TIMESTAMP WITH TIME ZONE,
            last_inbound_at TIMESTAMP WITH TIME ZONE,
            last_outbound_at TIMESTAMP WITH TIME ZONE,
            last_message_preview TEXT,
            unread_count INTEGER NOT NULL DEFAULT 0,
            is_archived BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_threads_tenant_updated ON communication_threads(tenant_id, updated_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_threads_tenant_channel_status ON communication_threads(tenant_id, channel, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_threads_tenant_entity ON communication_threads(tenant_id, entity_type, entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_threads_tenant_assignee ON communication_threads(tenant_id, assignee_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS communication_messages (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            thread_id VARCHAR(36) NOT NULL,
            channel VARCHAR(32) NOT NULL,
            message_type VARCHAR(32) NOT NULL DEFAULT 'text',
            direction VARCHAR(16) NOT NULL,
            sender_type VARCHAR(32),
            sender_id VARCHAR(36),
            sender_label VARCHAR(255),
            sender_address VARCHAR(255),
            recipient_type VARCHAR(32),
            recipient_id VARCHAR(36),
            recipient_label VARCHAR(255),
            recipient_address VARCHAR(255),
            subject VARCHAR(512),
            body_text TEXT,
            body_html TEXT,
            attachments_json JSONB,
            payload JSONB,
            external_message_ref VARCHAR(255),
            delivery_status VARCHAR(32) NOT NULL DEFAULT 'queued',
            error_message TEXT,
            sent_at TIMESTAMP WITH TIME ZONE,
            delivered_at TIMESTAMP WITH TIME ZONE,
            read_at TIMESTAMP WITH TIME ZONE,
            is_internal_note BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_messages_thread_created ON communication_messages(thread_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_messages_tenant_direction ON communication_messages(tenant_id, direction, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_messages_tenant_status ON communication_messages(tenant_id, delivery_status, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_messages_external_ref ON communication_messages(external_message_ref)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS communication_channel_accounts (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            channel VARCHAR(32) NOT NULL,
            account_label VARCHAR(255) NOT NULL,
            external_account_ref VARCHAR(255),
            inbox_address VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            settings_json JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_accounts_tenant_channel ON communication_channel_accounts(tenant_id, channel, is_active)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS communication_time_off_requests (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            requester_user_id VARCHAR(36) NOT NULL,
            requester_label VARCHAR(255),
            approver_user_id VARCHAR(36),
            approver_label VARCHAR(255),
            request_type VARCHAR(32) NOT NULL DEFAULT 'vacation',
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            start_date VARCHAR(32) NOT NULL,
            end_date VARCHAR(32) NOT NULL,
            partial_day VARCHAR(16),
            reason TEXT,
            decision_note TEXT,
            requested_at TIMESTAMP WITH TIME ZONE,
            decided_at TIMESTAMP WITH TIME ZONE,
            payload JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_timeoff_tenant_status ON communication_time_off_requests(tenant_id, status, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_timeoff_tenant_requester ON communication_time_off_requests(tenant_id, requester_user_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comm_timeoff_tenant_approver ON communication_time_off_requests(tenant_id, approver_user_id, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS communication_time_off_requests")
    op.execute("DROP TABLE IF EXISTS communication_channel_accounts")
    op.execute("DROP TABLE IF EXISTS communication_messages")
    op.execute("DROP TABLE IF EXISTS communication_threads")

