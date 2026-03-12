"""Models for requirement types (virtual requirements like CODE95_EVIDENCE, RIGHT_TO_WORK_BASIS)."""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from backend.app.db.base import Base
from .enums import RequirementType
from .mixins import TimestampMixin


class RequirementTypeDefinition(Base, TimestampMixin):
    """Определение типа требования (виртуальное требование).

    Например: CODE95_EVIDENCE, RIGHT_TO_WORK_BASIS.
    Может быть удовлетворено разными документами (satisfied_by_any).
    """

    __tablename__ = "requirement_type_definitions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "requirement_code",
            name="uq_requirement_type_tenant_code",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requirement_code: Mapped[RequirementType] = mapped_column(
        sa.Enum(RequirementType, name="requirement_type_enum", native_enum=False),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )

    # Правила удовлетворения требования (JSONB)
    # Формат: {
    #   "satisfied_by_any": [
    #     {
    #       "document_type": "DRIVING_LICENSE_CE",
    #       "status": ["VERIFIED"],
    #       "valid": true,
    #       "meta": {"code95": true}  # опционально
    #     }
    #   ],
    #   "satisfied_by_all": [...]  # для составных требований
    # }
    satisfaction_rules: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
    )


__all__ = ["RequirementTypeDefinition"]

