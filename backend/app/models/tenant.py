from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

from backend.app.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Table, Column
from sqlalchemy.sql import text
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
    tenant_links_as_agency: Mapped[list["TenantLink"]] = relationship(
        "TenantLink",
        foreign_keys="TenantLink.agency_tenant_id",
        back_populates="agency_tenant",
        cascade="all,delete-orphan",
    )
    tenant_links_as_client: Mapped[list["TenantLink"]] = relationship(
        "TenantLink",
        foreign_keys="TenantLink.client_tenant_id",
        back_populates="client_tenant",
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
    # Человекочитаемое название плана (например, "Free", "Pro", "Scale").
    # Для кода плана и логики ограничений используем сервисный слой.
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
    # Дополнительные лимиты по продукту (0 = неограничено, логика в сервисном слое).
    # Активные кандидаты в пайплайне (по всем вакансиям).
    max_candidates_active: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    # Активные вакансии (открытые / набирающие).
    max_vacancies_active: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    # Общее количество документов (для грубого лимита по storage, поверх max_storage_gb).
    max_documents: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    # Одновременные публичные порталы/ссылки статуса (кабинет кандидата / клиента).
    max_public_portal_links: Mapped[int] = mapped_column(
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


class TenantLink(Base, TimestampMixin):
    """Link agency tenant to client (company or employer tenant). Used for handoff feature."""

    __tablename__ = "tenant_links"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    agency_tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    client_tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    handoff_include_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", server_default="active", index=True
    )
    features_json: Mapped[Optional[dict]] = mapped_column(
        SQLiteJSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    portal_token: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True, index=True,
    )
    portal_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    agency_tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        foreign_keys=[agency_tenant_id],
        back_populates="tenant_links_as_agency",
    )
    client_tenant: Mapped[Optional["Tenant"]] = relationship(
        "Tenant",
        foreign_keys=[client_tenant_id],
        back_populates="tenant_links_as_client",
    )

    def get_handoff_enabled(self) -> bool:
        features = self.features_json or {}
        return bool(features.get("handoff_enabled", False))

    def get_contact_policy(self) -> dict:
        """Return contact_attempts policy: max_attempts, post_action, enabled."""
        features = self.features_json or {}
        policy = features.get("contact_policy") or {}
        # Безопасно приводим max_attempts к int, падать из‑за некорректного значения в JSON нельзя.
        raw_max_attempts = policy.get("max_attempts")
        try:
            max_attempts = int(raw_max_attempts) if raw_max_attempts not in (None, "") else 3
        except Exception:
            max_attempts = 3
        return {
            "enabled": bool(policy.get("enabled", False)),
            "max_attempts": max_attempts,
            "post_action": policy.get("post_action") or "auto_reject",  # auto_reject | stage_change
            "stage_code": policy.get("stage_code"),  # if post_action=stage_change
        }


class TenantUsageMetric(str, Enum):
    """Типы метрик потребления для биллинга/ограничений.

    Храним как строки, чтобы удобно расширять без миграций ENUM.
    """

    documents_uploaded = "documents_uploaded"
    candidates_created = "candidates_created"
    notifications_sent = "notifications_sent"
    public_links_created = "public_links_created"
    conversion_actions = "conversion_actions"
    automation_runs = "automation_runs"


class TenantUsage(Base, TimestampMixin):
    """Агрегированные usage-метрики по арендаторам (tenant) и периоду.

    Используется для мягких и жёстких лимитов (N операций в месяц и т.п.).
    """

    __tablename__ = "tenant_usage"
    __table_args__ = (
        sa.UniqueConstraint(
            "tenant_id",
            "metric",
            "period_start",
            "period_end",
            name="uq_tenant_usage_period",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Строковое имя метрики (см. TenantUsageMetric). Не жёсткий ENUM в БД для гибкости.
    metric: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    period_start: Mapped[Date] = mapped_column(Date, nullable=False)
    period_end: Mapped[Date] = mapped_column(Date, nullable=False)
    value: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", backref="usage")


__all__ = [
    "Tenant",
    "TenantLicense",
    "TenantLink",
    "TenantType",
    "TenantStatus",
    "TenantSeatRequest",
    "TenantSeatRequestStatus",
    "TenantVacancyAccess",
    "TenantUsage",
    "TenantUsageMetric",
]
