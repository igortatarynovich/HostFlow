from __future__ import annotations

from typing import Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin


class FleetVehicle(Base, TimestampMixin):
    __tablename__ = "fleet_vehicles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    internal_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    registration_plate: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vin: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    operating_company_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
