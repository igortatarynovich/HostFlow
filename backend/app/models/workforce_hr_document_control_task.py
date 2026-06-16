"""Per-document HR control task (owner / next action / due date / comment / status)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.workforce_employee import WorkforceEmployee


class WorkforceHrDocumentControlTask(Base, TimestampMixin):
    __tablename__ = "workforce_hr_document_control_tasks"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "employee_id",
            "document_code",
            name="uq_wf_hr_doc_ctrl_task_employee_doc",
        ),
        {"extend_existing": True},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    owner: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    next_action: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    next_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", server_default="open")

    employee: Mapped["WorkforceEmployee"] = relationship(
        "WorkforceEmployee",
        foreign_keys=[employee_id],
    )

