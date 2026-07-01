"""PIT-oriented tax profile for a workforce employee (storage; not a payroll calculator)."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.workforce_employee import WorkforceEmployee


class WorkforceTaxProfile(Base, TimestampMixin):
    __tablename__ = "workforce_tax_profiles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )

    tax_residency_country: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    tax_office: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pit2_submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    pit2_monthly_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    tax_deductible_costs_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    young_person_relief: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    employee: Mapped["WorkforceEmployee"] = relationship(
        "WorkforceEmployee",
        foreign_keys=[employee_id],
        back_populates="tax_profile",
    )
