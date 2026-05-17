"""HR acceptance review state (stage A): decision workflow before employment approval."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

HR_REVIEW_STATUS_IN_PROGRESS = "hr_review_in_progress"
HR_REVIEW_STATUS_WAITING_DOCUMENTS = "waiting_documents"
HR_REVIEW_STATUS_WAITING_PAYMENTS = "waiting_payments"
HR_REVIEW_STATUS_WAITING_WORK_PERMIT = "waiting_work_permit"
HR_REVIEW_STATUS_WAITING_RED_PAPER = "waiting_red_paper"
HR_REVIEW_STATUS_APPROVED = "approved_for_employment"
HR_REVIEW_STATUS_RETURNED = "returned_to_recruitment"
HR_REVIEW_STATUS_REJECTED = "rejected_by_hr"

HR_REVIEW_TERMINAL_STATUSES = frozenset(
    {
        HR_REVIEW_STATUS_APPROVED,
        HR_REVIEW_STATUS_RETURNED,
        HR_REVIEW_STATUS_REJECTED,
    }
)

HR_REVIEW_ACTIVE_STATUSES = frozenset(
    {
        HR_REVIEW_STATUS_IN_PROGRESS,
        HR_REVIEW_STATUS_WAITING_DOCUMENTS,
        HR_REVIEW_STATUS_WAITING_PAYMENTS,
        HR_REVIEW_STATUS_WAITING_WORK_PERMIT,
        HR_REVIEW_STATUS_WAITING_RED_PAPER,
    }
)


class WorkforceHrReview(Base, TimestampMixin):
    __tablename__ = "workforce_hr_reviews"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", name="uq_workforce_hr_review_tenant_employee"),
        {"extend_existing": True},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workforce_employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    handoff_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("candidate_handoffs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        default=HR_REVIEW_STATUS_IN_PROGRESS,
        server_default=HR_REVIEW_STATUS_IN_PROGRESS,
    )
    checklist_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    decision_basis_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    blockers_json: Mapped[Optional[list[Any]]] = mapped_column(JSONType, nullable=True)

    corrections_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    return_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    decided_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
