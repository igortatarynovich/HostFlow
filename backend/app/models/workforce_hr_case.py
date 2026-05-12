"""Operational HR case row linked to WorkforceEmployee (MVP before full hr_case product table)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class WorkforceHrCase(Base, TimestampMixin):
    __tablename__ = "workforce_hr_cases"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", name="uq_workforce_hr_case_tenant_employee"),
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
    source_candidate_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", server_default="open")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
