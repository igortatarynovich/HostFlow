"""Per-employee fee rows (work permit / red paper) — gates downstream HR steps."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin


class WorkforceWorkEligibilityPaymentRequirement(Base, TimestampMixin):
    __tablename__ = "workforce_work_eligibility_payment_requirements"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    requirement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="PLN")
    payment_status: Mapped[str] = mapped_column(String(16), nullable=False, default="not_required")
    due_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    receipt_document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    blocks_step: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
