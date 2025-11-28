from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin, now_utc

JSONType = JSON().with_variant(JSONB, "postgresql")


def _uuid_str() -> str:
    return str(uuid.uuid4())


class ServiceUnit(str, Enum):
    piece = "piece"
    person = "person"
    hour = "hour"
    package = "package"


class ServiceOrderStatus(str, Enum):
    draft = "draft"
    quoted = "quoted"
    approved = "approved"
    scheduled = "scheduled"
    in_progress = "in_progress"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"


class ServiceItemStatus(str, Enum):
    pending = "pending"
    scheduled = "scheduled"
    in_progress = "in_progress"
    delivered = "delivered"
    cancelled = "cancelled"


class ServiceScheduleStatus(str, Enum):
    reserved = "reserved"
    confirmed = "confirmed"
    completed = "completed"
    no_show = "no_show"
    cancelled = "cancelled"


class Service(Base, TimestampMixin):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_uuid_str,
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit: Mapped[ServiceUnit] = mapped_column(
        String(20), nullable=False, default=ServiceUnit.piece.value
    )
    base_price: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")
    vat_rate: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=23)
    requires_schedule: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    requires_candidate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    result_document_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    requires_documents: Mapped[Optional[List[str]]] = mapped_column(
        JSONType, nullable=True
    )
    sla_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=True, default=dict
    )

    items: Mapped[List["ServiceItem"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_services_tenant_code"),
        Index("ix_services_tenant_active", "tenant_id", "is_active"),
    )


class ServiceOrder(Base, TimestampMixin):
    __tablename__ = "service_orders"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_uuid_str,
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    candidate_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vacancy_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("vacancies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[ServiceOrderStatus] = mapped_column(
        String(32),
        nullable=False,
        default=ServiceOrderStatus.draft.value,
    )
    total_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")
    vat_total: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audit: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    items: Mapped[List["ServiceItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "((CASE WHEN candidate_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN vacancy_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN company_id IS NOT NULL THEN 1 ELSE 0 END)) = 1",
            name="ck_service_orders_owner",
        ),
        Index("ix_service_orders_tenant_status", "tenant_id", "status"),
    )


class ServiceItem(Base, TimestampMixin):
    __tablename__ = "service_items"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_uuid_str,
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("service_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    qty: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    vat_rate: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=0)
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    status: Mapped[ServiceItemStatus] = mapped_column(
        String(32),
        nullable=False,
        default=ServiceItemStatus.pending.value,
    )
    required_documents: Mapped[Optional[List[str]]] = mapped_column(
        JSONType, nullable=True
    )
    result_document_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    order: Mapped["ServiceOrder"] = relationship(back_populates="items", lazy="selectin")
    service: Mapped["Service"] = relationship(back_populates="items", lazy="selectin")
    schedules: Mapped[List["ServiceSchedule"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )
    attachments: Mapped[List["ServiceAttachment"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_service_items_tenant_status", "tenant_id", "status"),
    )


class ServiceSchedule(Base, TimestampMixin):
    __tablename__ = "service_schedule"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_uuid_str,
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("service_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    slot_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    slot_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[ServiceScheduleStatus] = mapped_column(
        String(32),
        nullable=False,
        default=ServiceScheduleStatus.reserved.value,
    )
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    item: Mapped["ServiceItem"] = relationship(back_populates="schedules", lazy="selectin")

    __table_args__ = (
        Index("ix_service_schedule_tenant_status", "tenant_id", "status"),
    )


class ServiceAttachment(Base):
    __tablename__ = "service_attachments"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_uuid_str,
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("service_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[str] = mapped_column(String(36), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc
    )

    item: Mapped["ServiceItem"] = relationship(back_populates="attachments", lazy="selectin")
