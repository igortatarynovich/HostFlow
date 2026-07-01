"""Models for stage gates (блокировки этапов)."""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from backend.app.db.base import Base
from .enums import GateCode
from .mixins import TimestampMixin


class Gate(Base, TimestampMixin):
    """Stage gate (блокировка этапа).

    Определяет, какие требования/документы должны быть выполнены для прохождения этапа.
    """

    __tablename__ = "gates"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "gate_code",
            name="uq_gate_tenant_code",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    gate_code: Mapped[GateCode] = mapped_column(
        sa.Enum(GateCode, name="gate_code_enum", native_enum=False),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocks_stage: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Название этапа, который блокируется"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    order: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=text("0")
    )


__all__ = ["Gate"]

