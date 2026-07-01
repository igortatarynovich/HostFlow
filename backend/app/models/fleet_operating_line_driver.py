from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import uuid4

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin


class FleetOperatingLineDriver(Base, TimestampMixin):
    __tablename__ = "fleet_operating_line_drivers"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    line_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fleet_operating_lines.id", ondelete="CASCADE"), index=True, nullable=False
    )
    fleet_driver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fleet_drivers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    work_model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fleet_work_models.id", ondelete="RESTRICT"), nullable=False
    )
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
