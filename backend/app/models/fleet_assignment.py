from __future__ import annotations

from datetime import date
from uuid import uuid4

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin


class FleetAssignment(Base, TimestampMixin):
    """Planned or active pairing of vehicle (and optionally trailer/driver) on an operating line."""

    __tablename__ = "fleet_assignments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    line_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fleet_operating_lines.id", ondelete="CASCADE"), index=True, nullable=False
    )
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fleet_vehicles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    trailer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("fleet_trailers.id", ondelete="SET NULL"), index=True, nullable=True
    )
    primary_driver_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("fleet_drivers.id", ondelete="SET NULL"), index=True, nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned", server_default="planned")
    service_start: Mapped[date] = mapped_column(Date(), nullable=False)
    service_end: Mapped[date | None] = mapped_column(Date(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
