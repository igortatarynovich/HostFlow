"""Agreed-terms snapshot for one Employment.

``hr_employments`` keeps the identity and the lifecycle. This row is
``employment_terms.v1``. It is not read from the vacancy, the contract
card, or payroll.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

DURATION_FIXED = "fixed"
DURATION_INDEFINITE = "indefinite"

PROBATION_NONE = "none"
PROBATION_DATED = "dated"
PROBATION_UNDETERMINED = "undetermined"


class HrEmploymentTerms(Base, TimestampMixin):
    __tablename__ = "hr_employment_terms"
    __table_args__ = (
        CheckConstraint(
            "duration IN ('fixed', 'indefinite')",
            name="ck_hr_employment_terms_duration",
        ),
        CheckConstraint(
            "(duration = 'fixed' AND fixed_term_end IS NOT NULL) "
            "OR (duration = 'indefinite' AND fixed_term_end IS NULL)",
            name="ck_hr_employment_terms_fixed_end",
        ),
        CheckConstraint(
            "(probation_status = 'none' AND probation_end IS NULL) "
            "OR (probation_status = 'dated' AND probation_end IS NOT NULL) "
            "OR (probation_status = 'undetermined' AND probation_end IS NULL)",
            name="ck_hr_employment_terms_probation",
        ),
        Index(
            "uq_hr_employment_terms_one_current",
            "employment_id",
            unique=True,
            sqlite_where=text("is_current = 1"),
            postgresql_where=text("is_current"),
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
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False)

    position: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_basis: Mapped[str] = mapped_column(String(64), nullable=False)
    work_time_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    work_time_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    work_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workplace: Mapped[str] = mapped_column(String(255), nullable=False)
    compensation_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    compensation_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    compensation_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    duration: Mapped[str] = mapped_column(String(16), nullable=False)
    fixed_term_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    probation_status: Mapped[str] = mapped_column(String(16), nullable=False)
    probation_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    intended_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    default_vacancy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
