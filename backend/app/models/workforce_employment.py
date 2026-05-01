from __future__ import annotations

from datetime import date
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class WorkforceEmployment(Base, TimestampMixin):
    """Contract / employment terms for a workforce employee (may have history rows per employee)."""

    __tablename__ = "workforce_employments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    contract_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    rate_model: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    schedule: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    conditions_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vacancy_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
