
from __future__ import annotations
import uuid

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
)
from sqlalchemy import JSON
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin, now_utc

JSONType = JSON().with_variant(JSONB, "postgresql")


class Role(str, Enum):
    """Tenant RBAC roles."""

    superadmin = "superadmin"
    administrator = "administrator"
    supervisor = "supervisor"
    recruiter = "recruiter"
    client_manager = "client_manager"
    client_processor = "client_processor"
    compliance_officer = "compliance_officer"
    hr_officer = "hr_officer"
    viewer = "viewer"
    admin = administrator
    owner = administrator
    manager = supervisor


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="role", native_enum=False),
        nullable=False,
        default=Role.viewer,
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    short_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True, default=dict
    )
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    supervisor_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    supervisor: Mapped["User | None"] = relationship(
        "User", remote_side="User.id", back_populates="recruiters", lazy="selectin"
    )
    recruiters: Mapped[List["User"]] = relationship(
        "User", back_populates="supervisor", lazy="selectin"
    )

    def mark_deleted(self) -> None:
        self.is_active = False
        self.deleted_at = self.deleted_at or now_utc()

    def revive(self) -> None:
        self.is_active = True
        self.deleted_at = None
