from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Table, Column
from sqlalchemy.sql import text

from backend.app.db.base import Base
from .mixins import TimestampMixin
from .user import User


user_memberships = Base.metadata.tables.get("user_memberships")
if user_memberships is None:
    user_memberships = Table(
        "user_memberships",
        Base.metadata,
        Column("id", String(36), primary_key=True),
        Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        Column("tenant_id", String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        Column("role", String(32), nullable=False, index=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
        Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_user_membership_user_tenant"),
        extend_existing=True,
    )


class TenantType(str, Enum):
    agency = "agency"
    company = "company"
    platform = "platform"


class TenantStatus(str, Enum):
    active = "active"
    suspended = "suspended"
    trial = "trial"


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    api_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # JSON settings care for different backends
    settings: Mapped[Optional[dict]] = mapped_column(
        SQLiteJSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict,
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workspace_label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    logo_meta: Mapped[Optional[dict]] = mapped_column(
        SQLiteJSON().with_variant(JSONB, "postgresql"), nullable=True
    )

    users = relationship(User, secondary=user_memberships, viewonly=True)
    type: Mapped[TenantType] = mapped_column(
        SAEnum(TenantType, name="tenant_type_enum", native_enum=False),
        nullable=False,
        default=TenantType.agency,
        server_default=TenantType.agency.value,
    )
    parent_tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[TenantStatus] = mapped_column(
        SAEnum(TenantStatus, name="tenant_status_enum", native_enum=False),
        nullable=False,
        default=TenantStatus.active,
        server_default=TenantStatus.active.value,
    )
    client_portal_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("1"),
    )
    status_sharing_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("0"),
    )

    parent: Mapped["Tenant | None"] = relationship(
        "Tenant",
        remote_side="Tenant.id",
        back_populates="children",
    )
    children: Mapped[list["Tenant"]] = relationship(
        "Tenant",
        back_populates="parent",
        cascade="all,delete-orphan",
    )
    license: Mapped["TenantLicense | None"] = relationship(
        "TenantLicense",
        back_populates="tenant",
        uselist=False,
        cascade="all,delete-orphan",
    )
    seat_requests: Mapped[list["TenantSeatRequest"]] = relationship(
        "TenantSeatRequest",
        back_populates="tenant",
        cascade="all,delete-orphan",
    )
    vacancy_access: Mapped[list["TenantVacancyAccess"]] = relationship(
        "TenantVacancyAccess",
        back_populates="tenant",
        cascade="all,delete-orphan",
    )


class TenantLicense(Base, TimestampMixin):
    __tablename__ = "tenant_licenses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    plan: Mapped[str] = mapped_column(String(64), nullable=False)
    max_recruiters: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    max_supervisors: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    max_client_managers: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    max_viewers: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    max_storage_gb: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    max_companies: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    expires_at: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("0"),
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tenant: Mapped[Tenant] = relationship(
        Tenant,
        back_populates="license",
    )


class TenantSeatRequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class TenantSeatRequest(Base, TimestampMixin):
    __tablename__ = "tenant_seat_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TenantSeatRequestStatus] = mapped_column(
        SAEnum(
            TenantSeatRequestStatus,
            name="tenant_seat_request_status_enum",
            native_enum=False,
        ),
        nullable=False,
        default=TenantSeatRequestStatus.pending,
        server_default=TenantSeatRequestStatus.pending.value,
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="seat_requests")


class TenantVacancyAccess(Base, TimestampMixin):
    __tablename__ = "tenant_vacancy_access"

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    vacancy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        primary_key=True,
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="vacancy_access")


__all__ = [
    "Tenant",
    "TenantLicense",
    "TenantType",
    "TenantStatus",
    "TenantSeatRequest",
    "TenantSeatRequestStatus",
]
