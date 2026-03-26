"""Stores processed Stripe webhook event ids for idempotency (§2.18)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base

from .mixins import now_utc


class StripeWebhookEventLog(Base):
    __tablename__ = "stripe_webhook_event_log"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
