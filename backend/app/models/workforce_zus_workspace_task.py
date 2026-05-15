"""Operational ZUS workspace tasks (queue; not ZUS API integration)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

if TYPE_CHECKING:
    from backend.app.models.workforce_employee import WorkforceEmployee


class WorkforceZusWorkspaceTask(Base, TimestampMixin):
    __tablename__ = "workforce_zus_workspace_tasks"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )

    workspace_lane: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    task_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    form_kind: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    form_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", server_default="open", index=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    assigned_hr_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    export_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    checklist_json: Mapped[Optional[Any]] = mapped_column(JSONType, nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["WorkforceEmployee"] = relationship(
        "WorkforceEmployee",
        back_populates="zus_workspace_tasks",
        foreign_keys=[employee_id],
    )
