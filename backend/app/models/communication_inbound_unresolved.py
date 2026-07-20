"""C0.2 — explicit unresolved inbound queue (no silent drops)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

UNRESOLVED_STATUS_OPEN = "open"
UNRESOLVED_STATUS_RESOLVED = "resolved"
UNRESOLVED_STATUS_DISMISSED = "dismissed"


class CommunicationInboundUnresolved(Base, TimestampMixin):
    """Queue row when inbound could not be deterministically linked to an entity."""

    __tablename__ = "communication_inbound_unresolved"
    __table_args__ = (
        Index(
            "ix_comm_inbound_unresolved_tenant_status",
            "tenant_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_comm_inbound_unresolved_tenant_thread",
            "tenant_id",
            "thread_id",
        ),
        Index(
            "ix_comm_inbound_unresolved_tenant_message",
            "tenant_id",
            "message_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    external_message_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    resolution_reason: Mapped[str] = mapped_column(
        String(64), nullable=False, default="unresolved"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=UNRESOLVED_STATUS_OPEN
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    details_json: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


__all__ = [
    "CommunicationInboundUnresolved",
    "UNRESOLVED_STATUS_OPEN",
    "UNRESOLVED_STATUS_RESOLVED",
    "UNRESOLVED_STATUS_DISMISSED",
]
