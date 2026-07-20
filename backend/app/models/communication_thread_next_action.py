"""C1.2 — ThreadNextAction: platform entity (not a Thread field)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

NEXT_ACTION_STATUS_ACTIVE = "active"
NEXT_ACTION_STATUS_COMPLETED = "completed"
NEXT_ACTION_STATUS_CANCELLED = "cancelled"

NEXT_ACTION_SOURCE_MANUAL = "manual"
NEXT_ACTION_SOURCE_AUTOMATION = "automation"


class CommunicationThreadNextAction(Base, TimestampMixin):
    __tablename__ = "communication_thread_next_actions"
    __table_args__ = (
        Index("ix_comm_tna_tenant_thread_created", "tenant_id", "thread_id", "created_at"),
        Index("ix_comm_tna_tenant_status", "tenant_id", "status", "due_at"),
        # One active next action per thread — enforced in app + partial unique index (migration).
        Index("ix_comm_tna_tenant_thread_status", "tenant_id", "thread_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=NEXT_ACTION_STATUS_ACTIVE
    )
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default=NEXT_ACTION_SOURCE_MANUAL
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)

    def to_projection(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "thread_id": str(self.thread_id),
            "action_type": self.action_type,
            "owner_id": self.owner_id,
            "due_at": self.due_at.isoformat() if self.due_at is not None else None,
            "status": self.status,
            "source": self.source,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at is not None
            else None,
            "completed_by": self.completed_by,
            "note": self.note,
        }


__all__ = [
    "CommunicationThreadNextAction",
    "NEXT_ACTION_STATUS_ACTIVE",
    "NEXT_ACTION_STATUS_COMPLETED",
    "NEXT_ACTION_STATUS_CANCELLED",
    "NEXT_ACTION_SOURCE_MANUAL",
    "NEXT_ACTION_SOURCE_AUTOMATION",
]
