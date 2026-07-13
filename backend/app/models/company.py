from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from .vacancy import Vacancy


def now_utc() -> datetime:
    # простой UTC now, чтобы всегда проставлялось на стороне Python
    return datetime.utcnow()


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    owner_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    manager_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255))
    tax_id: Mapped[Optional[str]] = mapped_column(String(64))
    phone: Mapped[Optional[str]] = mapped_column(String(64))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    website: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(String(2000))
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    country: Mapped[Optional[str]] = mapped_column(String(64))
    city: Mapped[Optional[str]] = mapped_column(String(128))
    address: Mapped[Optional[str]] = mapped_column(String(255))

    # Party (unified B2B/B2C counterparty) — companies row is the canonical Party record.
    party_entity_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="company",
        server_default=text("'company'"),
    )
    party_business_roles: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    client_stage: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    client_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_account_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    # JSON-поля: используем SQLite JSON + PostgreSQL JSONB
    _JSONType = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    contacts: Mapped[dict] = mapped_column(
        _JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    extra: Mapped[dict] = mapped_column(
        _JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    enabled_modules: Mapped[Optional[dict]] = mapped_column(
        _JSONType,
        nullable=True,
        default=None,
    )

    # ДВА уровня дефолтов: python-side + server_default — чтобы не ловить
    # NOT NULL даже если миграции отстают
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    vacancies: Mapped[list["Vacancy"]] = relationship(
        "Vacancy",
        back_populates="company",
        lazy="selectin"
    )

    __table_args__ = (
        Index("ix_companies_tenant_name", "tenant_id", "name"),
        Index("ix_companies_tenant_tax_id", "tenant_id", "tax_id"),
    )


class CandidateVacancy(Base):
    """
    Связь кандидата с вакансией (многие-ко-многим + статус).
    """

    __tablename__ = "candidate_vacancies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    candidate_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    vacancy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vacancies.id"),
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(32), default="applied", index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        Index(
            "ix_candvac_tenant_cand_vac",
            "tenant_id",
            "candidate_id",
            "vacancy_id",
            unique=True,
        ),
    )
