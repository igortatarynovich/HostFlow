"""Restore CommunicationDelivery model (B-1 SMS / email journal)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import now_utc

JSONType = MutableDict.as_mutable(JSONB().with_variant(SQLiteJSON(), "sqlite"))

DELIVERY_STATUS_QUEUED = "queued"
DELIVERY_STATUS_ACCEPTED = "accepted"
DELIVERY_STATUS_SENT = "sent"
DELIVERY_STATUS_DELIVERED = "delivered"
DELIVERY_STATUS_UNDELIVERED = "undelivered"  # legacy alias → undeliverable
DELIVERY_STATUS_UNDELIVERABLE = "undeliverable"
DELIVERY_STATUS_FAILED = "failed"
DELIVERY_STATUS_REJECTED = "rejected"
DELIVERY_STATUS_BOUNCED = "bounced"
DELIVERY_STATUS_EXPIRED = "expired"
DELIVERY_STATUS_CANCELLED = "cancelled"
DELIVERY_STATUS_UNKNOWN = "unknown"  # legacy; normalize via delivery_canon

DELIVERY_CHANNEL_SMS = "sms"
DELIVERY_CHANNEL_EMAIL = "email"

DELIVERY_PROVIDER_SMSAPI_PL = "smsapi_pl"
DELIVERY_PROVIDER_SMTP = "smtp"
DELIVERY_PROVIDER_TEST = "test"

PURPOSE_QUESTIONNAIRE_INVITE = "questionnaire_invite"


class CommunicationDelivery(Base):
    """Outbound communication delivery records (SMS, email, …)."""

    __tablename__ = "communication_deliveries"
    __table_args__ = (
        Index("ix_communication_deliveries_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_communication_deliveries_external_message_id", "external_message_id"),
        Index(
            "uq_communication_deliveries_idempotency",
            "tenant_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    invite_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("lead_questionnaire_invites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recipient_normalized: Mapped[str] = mapped_column(String(32), nullable=False)
    template_key: Mapped[str] = mapped_column(String(128), nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    message_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    encoding: Mapped[str] = mapped_column(String(16), nullable=False, default="gsm7", server_default="gsm7")
    parts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    external_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DELIVERY_STATUS_QUEUED,
        server_default=DELIVERY_STATUS_QUEUED,
    )
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
