"""HR Legal Eligibility checkpoint for one Employment.

The row is the HR audit. It is not a second legalization model and it is
not an Employment state.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class HrLegalEligibilityGateDecision(Base):
    __tablename__ = "hr_legal_eligibility_gate_decisions"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('pass', 'fail', 'blocked')",
            name="ck_hr_legal_eligibility_gate_outcome",
        ),
        {"extend_existing": True},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hr_employments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    citizenship_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stay_basis: Mapped[str | None] = mapped_column(String(32), nullable=True)
    work_authorization_basis: Mapped[str | None] = mapped_column(String(32), nullable=True)
    valid_for_this_employment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    client_company_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    vacancy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
