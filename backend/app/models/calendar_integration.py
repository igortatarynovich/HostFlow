from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class CalendarConnection(Base, TimestampMixin):
    __tablename__ = "calendar_connections"
    __table_args__ = (
        Index("ix_calendar_connections_tenant_provider", "tenant_id", "provider", "status"),
        Index("ix_calendar_connections_tenant_user", "tenant_id", "user_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # google|microsoft
    account_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    scopes_json: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    token_meta_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CalendarChannel(Base, TimestampMixin):
    __tablename__ = "calendar_channels"
    __table_args__ = (
        Index("ix_calendar_channels_conn_provider", "connection_id", "provider", "health_state"),
        Index("ix_calendar_channels_tenant_expires", "tenant_id", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    renew_after: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    health_state: Mapped[str] = mapped_column(String(32), nullable=False, default="healthy")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


class CalendarItem(Base, TimestampMixin):
    __tablename__ = "calendar_items"
    __table_args__ = (
        Index("ix_calendar_items_tenant_start", "tenant_id", "starts_at"),
        Index("ix_calendar_items_tenant_owner", "tenant_id", "owner_id", "starts_at"),
        Index("ix_calendar_items_tenant_kind_status", "tenant_id", "kind", "status", "starts_at"),
        Index("ix_calendar_items_tenant_entity", "tenant_id", "linked_entity_type", "linked_entity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="event")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    linked_entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    linked_entity_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="hostflow")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


class CalendarItemLink(Base, TimestampMixin):
    __tablename__ = "calendar_item_links"
    __table_args__ = (
        Index("ix_calendar_item_links_item_provider", "calendar_item_id", "provider"),
        Index("ix_calendar_item_links_provider_event", "provider", "provider_event_id"),
        Index("ix_calendar_item_links_tenant_state", "tenant_id", "sync_state", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    calendar_item_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    connection_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_version: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sync_state: Mapped[str] = mapped_column(String(32), nullable=False, default="synced")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


class CalendarSyncCursor(Base, TimestampMixin):
    __tablename__ = "calendar_sync_cursors"
    __table_args__ = (
        Index("ix_calendar_sync_cursors_connection", "connection_id", "provider", "calendar_ref"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    calendar_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cursor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cursor_meta_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CalendarSyncJob(Base, TimestampMixin):
    __tablename__ = "calendar_sync_jobs"
    __table_args__ = (
        Index("ix_calendar_sync_jobs_tenant_status", "tenant_id", "status", "created_at"),
        Index("ix_calendar_sync_jobs_tenant_source", "tenant_id", "source_kind", "created_at"),
        Index("ix_calendar_sync_jobs_dedupe", "dedupe_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)  # google_webhook|...
    operation: Mapped[str] = mapped_column(String(32), nullable=False, default="ingest")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


class IntegrationActionLog(Base, TimestampMixin):
    __tablename__ = "integration_action_logs"
    __table_args__ = (
        Index("ix_integration_action_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_integration_action_logs_tenant_source", "tenant_id", "source", "created_at"),
        Index("ix_integration_action_logs_tenant_item", "tenant_id", "calendar_item_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    calendar_item_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="hostflow")  # hostflow|slack|teams
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    outcome: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


__all__ = [
    "CalendarConnection",
    "CalendarChannel",
    "CalendarItem",
    "CalendarItemLink",
    "CalendarSyncCursor",
    "CalendarSyncJob",
    "IntegrationActionLog",
]
