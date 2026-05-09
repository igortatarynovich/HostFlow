"""ActivityEvent model — audit log of Activity state transitions (ADR-012).

Source of truth for the audit-log companion of :class:`Activity`. Every
state transition (``created``, ``status_changed``, ``snoozed``,
``rescheduled``, ``reassigned``, ``completed``, ``cancelled``,
``escalated``) is recorded as one ``ActivityEvent`` row.

Phase 1.3 (``activity_layer_v1``) renames the table to ``activity_events``
and the FK column to ``activity_id``. Legacy attribute synonyms (kept
until Phase 4 cleanup):

- ``ActivityEvent.reminder_id`` → ``ActivityEvent.activity_id``

The legacy ``ReminderEvent`` name remains a thin re-export
(``models/reminder_event.py``) — ``ReminderEvent is ActivityEvent``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, synonym

from backend.app.db.base import Base
from .mixins import now_utc


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (
        Index("ix_activity_events_tenant", "tenant_id"),
        Index("ix_activity_events_activity", "activity_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    activity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    # ---- Legacy attribute synonym (Phase 1.3 §9.1, kept until Phase 4) ----
    reminder_id = synonym("activity_id")


__all__ = ["ActivityEvent"]
