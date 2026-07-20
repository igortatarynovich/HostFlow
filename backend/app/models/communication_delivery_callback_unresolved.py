"""C0.3 — unresolved delivery callback queue when delivery cannot be resolved."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

CALLBACK_UNRESOLVED_OPEN = "open"
CALLBACK_UNRESOLVED_RESOLVED = "resolved"
CALLBACK_UNRESOLVED_DISMISSED = "dismissed"


class CommunicationDeliveryCallbackUnresolved(Base, TimestampMixin):
    """Queue when a provider delivery callback cannot be bound to a delivery."""

    __tablename__ = "communication_delivery_callback_unresolved"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            "provider_event_id",
            name="uq_comm_delivery_callback_event",
        ),
        Index(
            "ix_comm_delivery_cb_unresolved_tenant_status",
            "tenant_id",
            "status",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_account_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CALLBACK_UNRESOLVED_OPEN
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False, default="unresolved")
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )

    resolved_delivery_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    resolved_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


__all__ = [
    "CommunicationDeliveryCallbackUnresolved",
    "CALLBACK_UNRESOLVED_OPEN",
    "CALLBACK_UNRESOLVED_RESOLVED",
    "CALLBACK_UNRESOLVED_DISMISSED",
]
