"""Tenant-scoped org units (departments / teams) and user membership."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = JSON().with_variant(JSONB, "postgresql")


class OrgUnit(Base, TimestampMixin):
    __tablename__ = "org_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("org_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(32), nullable=False, default="department")
    code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    leader_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    parent: Mapped[Optional["OrgUnit"]] = relationship(
        "OrgUnit",
        remote_side="OrgUnit.id",
        foreign_keys=[parent_id],
        back_populates="children",
    )
    children: Mapped[list["OrgUnit"]] = relationship(
        "OrgUnit",
        foreign_keys="OrgUnit.parent_id",
        back_populates="parent",
    )
    members: Mapped[list["OrgUnitMember"]] = relationship(
        "OrgUnitMember",
        back_populates="org_unit",
        cascade="all, delete-orphan",
        foreign_keys="OrgUnitMember.org_unit_id",
    )


class OrgUnitMember(Base, TimestampMixin):
    __tablename__ = "org_unit_members"
    __table_args__ = (
        UniqueConstraint("tenant_id", "org_unit_id", "user_id", name="uq_org_unit_member_tenant_unit_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    org_unit_id: Mapped[str] = mapped_column(String(36), ForeignKey("org_units.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role_in_unit: Mapped[str] = mapped_column(String(32), nullable=False, default="member")

    org_unit: Mapped["OrgUnit"] = relationship("OrgUnit", back_populates="members")
