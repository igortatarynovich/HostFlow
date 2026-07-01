from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from typing import Any

from sqlalchemy import create_engine


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _ensure_non_sqlite_schema() -> None:
    # Postgres/MySQL dev/prod path: use SQLAlchemy metadata for communications tables only.
    try:
        from backend.app.core.settings import settings
        from backend.app.models.communication import (
            CommunicationAllocationAudit,
            CommunicationChannelAccount,
            CommunicationCommandAudit,
            CommunicationMessage,
            CommunicationPlannerEvent,
            CommunicationThread,
            CommunicationTimeOffRequest,
        )
        from backend.app.db.base import Base
    except Exception as exc:
        print(f"[communications] non-sqlite ensure skipped imports ({exc})")
        return

    sync_url = str(getattr(settings, "SYNC_DATABASE_URL", "") or "").strip()
    if not sync_url or sync_url.startswith("sqlite"):
        return

    engine = create_engine(sync_url, future=True)
    try:
        Base.metadata.create_all(
            engine,
            tables=[
                CommunicationThread.__table__,
                CommunicationMessage.__table__,
                CommunicationChannelAccount.__table__,
                CommunicationTimeOffRequest.__table__,
                CommunicationAllocationAudit.__table__,
                CommunicationPlannerEvent.__table__,
                CommunicationCommandAudit.__table__,
            ],
        )
        print("[communications] ensured schema via SQLAlchemy create_all (non-sqlite)")
    finally:
        engine.dispose()


def ensure_communications_schema() -> None:
    """Ensure SQLite dev/test database has communications thread/message/account tables."""
    _ensure_non_sqlite_schema()
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()

        if not _table_exists(cur, "communication_threads"):
            cur.execute(
                """
                CREATE TABLE communication_threads (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    channel_account_id TEXT,
                    channel_thread_ref TEXT,
                    subject TEXT,
                    status TEXT NOT NULL DEFAULT 'open',
                    direction_hint TEXT,
                    entity_type TEXT,
                    entity_id TEXT,
                    linked_company_id TEXT,
                    linked_candidate_id TEXT,
                    owner_id TEXT,
                    assignee_id TEXT,
                    queue_assigned_by TEXT,
                    priority TEXT NOT NULL DEFAULT 'normal',
                    sla_due_at TEXT,
                    participants_json TEXT,
                    tags_json TEXT,
                    thread_meta TEXT,
                    last_message_at TEXT,
                    last_inbound_at TEXT,
                    last_outbound_at TEXT,
                    last_message_preview TEXT,
                    unread_count INTEGER NOT NULL DEFAULT 0,
                    is_archived INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_threads_tenant_updated ON communication_threads(tenant_id, updated_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_threads_tenant_channel_status ON communication_threads(tenant_id, channel, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_threads_tenant_entity ON communication_threads(tenant_id, entity_type, entity_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_threads_tenant_assignee ON communication_threads(tenant_id, assignee_id)")

        if not _table_exists(cur, "communication_messages"):
            cur.execute(
                """
                CREATE TABLE communication_messages (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    message_type TEXT NOT NULL DEFAULT 'text',
                    direction TEXT NOT NULL,
                    sender_type TEXT,
                    sender_id TEXT,
                    sender_label TEXT,
                    sender_address TEXT,
                    recipient_type TEXT,
                    recipient_id TEXT,
                    recipient_label TEXT,
                    recipient_address TEXT,
                    subject TEXT,
                    body_text TEXT,
                    body_html TEXT,
                    attachments_json TEXT,
                    payload TEXT,
                    external_message_ref TEXT,
                    delivery_status TEXT NOT NULL DEFAULT 'queued',
                    error_message TEXT,
                    sent_at TEXT,
                    delivered_at TEXT,
                    read_at TEXT,
                    is_internal_note INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_messages_thread_created ON communication_messages(thread_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_messages_tenant_direction ON communication_messages(tenant_id, direction, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_messages_tenant_status ON communication_messages(tenant_id, delivery_status, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_messages_external_ref ON communication_messages(external_message_ref)")

        if not _table_exists(cur, "communication_channel_accounts"):
            cur.execute(
                """
                CREATE TABLE communication_channel_accounts (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    account_label TEXT NOT NULL,
                    external_account_ref TEXT,
                    inbox_address TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    settings_json TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_accounts_tenant_channel ON communication_channel_accounts(tenant_id, channel, is_active)")

        if not _table_exists(cur, "communication_time_off_requests"):
            cur.execute(
                """
                CREATE TABLE communication_time_off_requests (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    requester_user_id TEXT NOT NULL,
                    requester_label TEXT,
                    approver_user_id TEXT,
                    approver_label TEXT,
                    request_type TEXT NOT NULL DEFAULT 'vacation',
                    status TEXT NOT NULL DEFAULT 'pending',
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    partial_day TEXT,
                    reason TEXT,
                    decision_note TEXT,
                    requested_at TEXT,
                    decided_at TEXT,
                    payload TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_timeoff_tenant_status ON communication_time_off_requests(tenant_id, status, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_timeoff_tenant_requester ON communication_time_off_requests(tenant_id, requester_user_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_timeoff_tenant_approver ON communication_time_off_requests(tenant_id, approver_user_id, created_at)")

        if not _table_exists(cur, "communication_allocation_audits"):
            cur.execute(
                """
                CREATE TABLE communication_allocation_audits (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    mode TEXT NOT NULL DEFAULT 'allocate',
                    channel TEXT NOT NULL,
                    thread_id TEXT,
                    actor_user_id TEXT,
                    strategy TEXT,
                    assigned INTEGER NOT NULL DEFAULT 0,
                    assignee_id TEXT,
                    reason TEXT,
                    evaluated_at TEXT,
                    candidates_json TEXT,
                    payload TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_alloc_audit_tenant_created ON communication_allocation_audits(tenant_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_alloc_audit_tenant_thread ON communication_allocation_audits(tenant_id, thread_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_alloc_audit_tenant_assignee ON communication_allocation_audits(tenant_id, assignee_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_alloc_audit_tenant_mode ON communication_allocation_audits(tenant_id, mode, created_at)")

        if not _table_exists(cur, "communication_planner_events"):
            cur.execute(
                """
                CREATE TABLE communication_planner_events (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    kind TEXT NOT NULL DEFAULT 'task',
                    status TEXT NOT NULL DEFAULT 'planned',
                    priority TEXT NOT NULL DEFAULT 'normal',
                    start_at TEXT NOT NULL,
                    end_at TEXT,
                    all_day INTEGER NOT NULL DEFAULT 0,
                    owner_id TEXT,
                    assignee_id TEXT,
                    entity_type TEXT,
                    entity_id TEXT,
                    linked_candidate_id TEXT,
                    linked_company_id TEXT,
                    source TEXT NOT NULL DEFAULT 'manual',
                    payload TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_planner_tenant_start ON communication_planner_events(tenant_id, start_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_planner_tenant_assignee ON communication_planner_events(tenant_id, assignee_id, start_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_planner_tenant_status ON communication_planner_events(tenant_id, status, start_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_planner_tenant_entity ON communication_planner_events(tenant_id, entity_type, entity_id)")

        if not _table_exists(cur, "communication_command_audits"):
            cur.execute(
                """
                CREATE TABLE communication_command_audits (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    command_id TEXT NOT NULL,
                    command_label TEXT,
                    actor_user_id TEXT,
                    action_count INTEGER NOT NULL DEFAULT 0,
                    actions_json TEXT,
                    payload TEXT,
                    executed_at TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_cmd_audit_tenant_created ON communication_command_audits(tenant_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_cmd_audit_tenant_thread ON communication_command_audits(tenant_id, thread_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_cmd_audit_tenant_actor ON communication_command_audits(tenant_id, actor_user_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_cmd_audit_tenant_cmd ON communication_command_audits(tenant_id, command_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_comm_cmd_audit_tenant_channel ON communication_command_audits(tenant_id, channel, created_at)")

        conn.commit()
        print("[communications] ensure_communications_schema executed")
