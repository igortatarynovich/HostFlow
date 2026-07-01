from __future__ import annotations

from datetime import date
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

_JSON_LIST = SQLiteJSON().with_variant(JSONB, "postgresql")


class FleetOperatingLine(Base, TimestampMixin):
    """Operational line: which fleet serves which client / contract (phase 1: metadata + companies FK)."""

    __tablename__ = "fleet_operating_lines"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")

    operating_company_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_company_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )

    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # 12 monthly multipliers (see fleet-driver-headcount-planning); nullable = use calculator defaults only.
    seasonality_month_factors: Mapped[Optional[list[Any]]] = mapped_column(_JSON_LIST, nullable=True)
