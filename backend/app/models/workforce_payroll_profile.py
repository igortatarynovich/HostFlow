from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class WorkforcePayrollProfile(Base, TimestampMixin):
    """Payroll-facing profile: storage + export hooks (no calculation engine in MVP)."""

    __tablename__ = "workforce_payroll_profiles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pay_type: Mapped[str] = mapped_column(String(64), nullable=False, default="mixed")
    base_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, default="PLN")
    calculation_system: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    pay_day_note: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    bank_account: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tax_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pit_declarations: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    allowances: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    deductions: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    payroll_status: Mapped[str] = mapped_column(String(64), nullable=False, default="missing_data")
    external_refs: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
