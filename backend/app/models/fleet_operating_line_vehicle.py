from __future__ import annotations

from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin


class FleetOperatingLineVehicle(Base, TimestampMixin):
    __tablename__ = "fleet_operating_line_vehicles"
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
    default_work_model_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("fleet_work_models.id", ondelete="SET NULL"), nullable=True
    )
