"""Notification event registry rows (P2) — event intent, not ADR-012 user delivery."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy import String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.document_expiry_notifications.constants import (
    EVENT_STATUS_OPEN,
    NOTIFICATION_EVENT_V1,
    SOURCE_LAYER,
)
from backend.app.models.mixins import TimestampMixin

JSONAnyType = SQLiteJSON().with_variant(JSONB, "postgresql")


class NotificationEvent(TimestampMixin, Base):
    """Idempotent expiry notification event registry (P2)."""

    __tablename__ = "notification_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "event_key", name="uq_notification_events_tenant_event_key"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    event_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    evaluation_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'" + NOTIFICATION_EVENT_V1 + "'"),
    )
    event_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_layer: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=text("'" + SOURCE_LAYER + "'"),
        index=True,
    )
    owner_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    document_type_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    document_runtime: Mapped[dict[str, Any]] = mapped_column(JSONAnyType, nullable=False)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata",
        JSONAnyType,
        nullable=True,
    )
    evaluated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'" + EVENT_STATUS_OPEN + "'"),
        index=True,
    )
