from __future__ import annotations

from typing import Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin


class FleetWorkModel(Base, TimestampMixin):
    """Rotation template: work_days + rest_days must equal cycle_length (days as abstract units)."""

    __tablename__ = "fleet_work_models"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    work_days: Mapped[int] = mapped_column(Integer, nullable=False)
    rest_days: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_length: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
