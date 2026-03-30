from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.db.tsvector_compat import TsVector
from .mixins import TimestampMixin


JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class CommunicationThread(Base, TimestampMixin):
    __tablename__ = "communication_threads"
    __table_args__ = (
        Index("ix_comm_threads_tenant_updated", "tenant_id", "updated_at"),
        Index("ix_comm_threads_tenant_channel_status", "tenant_id", "channel", "status"),
        Index("ix_comm_threads_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_comm_threads_tenant_assignee", "tenant_id", "assignee_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    own_company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    channel: Mapped[str] = mapped_column(String(32), nullable=False)  # email, whatsapp, telegram, ...
    channel_account_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    channel_thread_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    subject: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    direction_hint: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # inbound/outbound/mixed

    entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    linked_company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    linked_candidate_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    owner_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    queue_assigned_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # manual/round_robin/...
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    sla_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    participants_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    tags_json: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    thread_meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)

    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_inbound_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_outbound_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hostflow_search_tsv: Mapped[Optional[Any]] = mapped_column(TsVector, nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CommunicationMessage(Base, TimestampMixin):
    __tablename__ = "communication_messages"
    __table_args__ = (
        Index("ix_comm_messages_thread_created", "thread_id", "created_at"),
        Index("ix_comm_messages_tenant_direction", "tenant_id", "direction", "created_at"),
        Index("ix_comm_messages_tenant_status", "tenant_id", "delivery_status", "created_at"),
        Index("ix_comm_messages_external_ref", "external_message_ref"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    own_company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    thread_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")  # text/email/system/file
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # inbound/outbound/system

    sender_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # user/candidate/client/system
    sender_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    sender_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # email/phone/chat id

    recipient_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    recipient_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    recipient_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recipient_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    subject: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachments_json: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)

    external_message_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")  # queued/sent/delivered/read/failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_internal_note: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CommunicationChannelAccount(Base, TimestampMixin):
    __tablename__ = "communication_channel_accounts"
    __table_args__ = (
        Index("ix_comm_accounts_tenant_channel", "tenant_id", "channel", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    account_label: Mapped[str] = mapped_column(String(255), nullable=False)
    external_account_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    inbox_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


class CommunicationTimeOffRequest(Base, TimestampMixin):
    __tablename__ = "communication_time_off_requests"
    __table_args__ = (
        Index("ix_comm_timeoff_tenant_status", "tenant_id", "status", "created_at"),
        Index("ix_comm_timeoff_tenant_requester", "tenant_id", "requester_user_id", "created_at"),
        Index("ix_comm_timeoff_tenant_approver", "tenant_id", "approver_user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    requester_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requester_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approver_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    approver_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    request_type: Mapped[str] = mapped_column(String(32), nullable=False, default="vacation")  # vacation/day_off/sick_leave/other
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")  # pending/approved/rejected/cancelled
    start_date: Mapped[str] = mapped_column(String(32), nullable=False)  # ISO date
    end_date: Mapped[str] = mapped_column(String(32), nullable=False)  # ISO date
    partial_day: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # full/first_half/second_half

    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


class CommunicationAllocationAudit(Base, TimestampMixin):
    __tablename__ = "communication_allocation_audits"
    __table_args__ = (
        Index("ix_comm_alloc_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_comm_alloc_audit_tenant_thread", "tenant_id", "thread_id", "created_at"),
        Index("ix_comm_alloc_audit_tenant_assignee", "tenant_id", "assignee_id", "created_at"),
        Index("ix_comm_alloc_audit_tenant_mode", "tenant_id", "mode", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="allocate")  # allocate/preview
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    thread_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    strategy: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    assigned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    candidates_json: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


class CommunicationPlannerEvent(Base, TimestampMixin):
    __tablename__ = "communication_planner_events"
    __table_args__ = (
        Index("ix_comm_planner_tenant_start", "tenant_id", "start_at"),
        Index("ix_comm_planner_tenant_assignee", "tenant_id", "assignee_id", "start_at"),
        Index("ix_comm_planner_tenant_status", "tenant_id", "status", "start_at"),
        Index("ix_comm_planner_tenant_entity", "tenant_id", "entity_type", "entity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="task")  # task/call/meeting/followup/shift
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")  # planned/in_progress/done/cancelled
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    owner_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    linked_candidate_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    linked_company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")  # manual/import/system
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


class CommunicationCommandAudit(Base, TimestampMixin):
    __tablename__ = "communication_command_audits"
    __table_args__ = (
        Index("ix_comm_cmd_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_comm_cmd_audit_tenant_thread", "tenant_id", "thread_id", "created_at"),
        Index("ix_comm_cmd_audit_tenant_actor", "tenant_id", "actor_user_id", "created_at"),
        Index("ix_comm_cmd_audit_tenant_cmd", "tenant_id", "command_id", "created_at"),
        Index("ix_comm_cmd_audit_tenant_channel", "tenant_id", "channel", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    command_id: Mapped[str] = mapped_column(String(64), nullable=False)
    command_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actions_json: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "CommunicationThread",
    "CommunicationMessage",
    "CommunicationChannelAccount",
    "CommunicationTimeOffRequest",
    "CommunicationAllocationAudit",
    "CommunicationPlannerEvent",
    "CommunicationCommandAudit",
]
