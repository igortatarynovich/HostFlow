from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin


class ReminderStatus:
    new = "new"
    pending = "pending"
    sent = "sent"
    overdue = "overdue"
    done = "done"
    cancelled = "cancelled"


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"
    __table_args__ = (
        Index("ix_reminders_tenant_due", "tenant_id", "due_at"),
        Index("ix_reminders_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_reminders_assignee_remind", "tenant_id", "assignee_id", "remind_at"),
        Index("ix_reminders_assignee_due", "tenant_id", "assignee_id", "due_at"),
        Index("ix_reminders_status_due", "tenant_id", "status", "due_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    # Phase 2.6.G-5 Stage E — FK ``users.id ON DELETE SET NULL`` added so
    # deleting a user clears orphan reminder assignees instead of leaving
    # them as dangling UUIDs that surface in ``/app/tasks`` and the bell.
    # See ``docs/specs/manager-assignment.md`` §4 Stage E and Alembic
    # revision ``202604190002_owner_fk_set_null``.
    assignee_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    priority: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    channel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="internal")
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    remind_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    snoozed_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    recurrence_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ReminderStatus.pending
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = ["Reminder", "ReminderStatus"]
