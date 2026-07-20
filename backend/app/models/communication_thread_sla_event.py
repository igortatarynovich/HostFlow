"""C1.2 — SLA event clock (breach is always derived, never a stored SoT flag)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

SLA_EVENT_START = "start"
SLA_EVENT_PAUSE = "pause"
SLA_EVENT_RESUME = "resume"
SLA_EVENT_RESOLVE = "resolve"

SLA_EVENT_TYPES = frozenset(
    {SLA_EVENT_START, SLA_EVENT_PAUSE, SLA_EVENT_RESUME, SLA_EVENT_RESOLVE}
)


class CommunicationThreadSlaEvent(Base, TimestampMixin):
    __tablename__ = "communication_thread_sla_events"
    __table_args__ = (
        Index("ix_comm_sla_ev_tenant_thread_at", "tenant_id", "thread_id", "at"),
        Index("ix_comm_sla_ev_tenant_type", "tenant_id", "event_type", "at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


__all__ = [
    "CommunicationThreadSlaEvent",
    "SLA_EVENT_START",
    "SLA_EVENT_PAUSE",
    "SLA_EVENT_RESUME",
    "SLA_EVENT_RESOLVE",
    "SLA_EVENT_TYPES",
]
