"""C0.3 — immutable delivery attempt journal (append-only)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class CommunicationDeliveryAttempt(Base, TimestampMixin):
    """One send/delivery try. Retries create a new row — never overwrite."""

    __tablename__ = "communication_delivery_attempts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "delivery_id",
            "attempt_number",
            name="uq_comm_delivery_attempt_number",
        ),
        Index(
            "ix_comm_delivery_attempts_tenant_delivery",
            "tenant_id",
            "delivery_id",
            "attempt_number",
        ),
        Index(
            "ix_comm_delivery_attempts_tenant_message",
            "tenant_id",
            "message_id",
        ),
        Index(
            "ix_comm_delivery_attempts_provider_msg",
            "tenant_id",
            "provider",
            "provider_message_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    delivery_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_account_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Canonical attempt result (queued/accepted/sent/delivered/failed/…).
    canonical_result: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reason_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    retryable: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    safe_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_provider_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


__all__ = ["CommunicationDeliveryAttempt"]
