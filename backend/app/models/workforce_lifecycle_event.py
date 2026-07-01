"""HR lifecycle ledger event (domain-level employee history, not technical audit)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class WorkforceLifecycleEvent(Base, TimestampMixin):
    __tablename__ = "workforce_lifecycle_events"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )

    event_code: Mapped[str] = mapped_column(String(96), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    owner: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", server_default="open", index=True)
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(160), nullable=True, index=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(96), nullable=True)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    references_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    attachments_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
