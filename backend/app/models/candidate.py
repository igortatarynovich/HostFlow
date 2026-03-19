from __future__ import annotations

from datetime import datetime, date
from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String, Text, Integer, event, select, func, cast
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict, MutableList
from uuid import uuid4
import json


from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models import Company, Vacancy
    from .user import User


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    own_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("own_companies.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    short_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)

    first_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    last_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    first_name_latin: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    last_name_latin: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    phone_country_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    # Доп. контактные/личные поля

    # JSON-список языков
    languages = Column(SQLiteJSON, nullable=True)

    # этап в виде КОДА
    stage: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    status_reason: Mapped[Optional[list[str]]] = mapped_column(
        MutableList.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
        default=list,
    )
    
    # Теги/метки для организации и фильтрации кандидатов
    tags: Mapped[Optional[list[str]]] = mapped_column(
        MutableList.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
        default=list,
    )
    
    # Избранный кандидат (закладка)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manager: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)

    # НОВОЕ: привязки
    company_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    vacancy_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("vacancies.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    funnel_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("funnels.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    recruiter_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # служебные JSON/строки
    docs_progress: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default="{}"
    )
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="{}")
    personal_data: Mapped[Optional[dict]] = mapped_column(
        SQLiteJSON().with_variant(JSONB, "postgresql"), nullable=True, default=dict
    )
    contacts: Mapped[Optional[dict]] = mapped_column(
        SQLiteJSON().with_variant(JSONB, "postgresql"), nullable=True, default=dict
    )
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    origin: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
        default=dict,
    )
    intake_token: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    intake_token_created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    intake_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    intake_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    intake_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="draft")
    intake_state: Mapped[Optional[dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
        default=dict,
    )
    status_share_token: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    status_share_token_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status_share_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships (lazy joined for convenient reads)
    company: Mapped[Optional["Company"]] = relationship("Company", lazy="joined")
    vacancy: Mapped[Optional["Vacancy"]] = relationship("Vacancy", lazy="joined")
    recruiter: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[recruiter_id],
        lazy="selectin",
    )

    # Accessors for fields stored inside extra (JSON)
    def _get_extra(self) -> dict:
        try:
            return json.loads(self.extra or "{}")
        except Exception:
            return {}
    def _get_personal_data(self) -> dict:
        try:
            if isinstance(self.personal_data, dict):
                return self.personal_data
        except Exception:
            pass
        return {}

    def _set_personal_data(self, data: dict) -> None:
        self.personal_data = data or {}

    def _get_contacts(self) -> dict:
        try:
            if isinstance(self.contacts, dict):
                return self.contacts
        except Exception:
            pass
        return {}

    def _set_contacts(self, data: dict) -> None:
        self.contacts = data or {}

    def _set_extra(self, data: dict) -> None:
        self.extra = json.dumps(data or {})

    @property
    def country_code(self) -> Optional[str]:
        pd = self._get_personal_data()
        if pd.get("country_code") is not None:
            return pd.get("country_code")
        return self._get_extra().get("country_code")

    @country_code.setter
    def country_code(self, value: Optional[str]) -> None:
        pd = self._get_personal_data()
        pd["country_code"] = value
        self._set_personal_data(pd)
        data = self._get_extra()
        data["country_code"] = value
        self._set_extra(data)

    @property
    def city(self) -> Optional[str]:
        pd = self._get_personal_data()
        if pd.get("city") is not None:
            return pd.get("city")
        return self._get_extra().get("city")

    @city.setter
    def city(self, value: Optional[str]) -> None:
        pd = self._get_personal_data()
        pd["city"] = value
        self._set_personal_data(pd)
        data = self._get_extra()
        data["city"] = value
        self._set_extra(data)

    @property
    def address(self) -> Optional[str]:
        pd = self._get_personal_data()
        if pd.get("address") is not None:
            return pd.get("address")
        return self._get_extra().get("address")

    @address.setter
    def address(self, value: Optional[str]) -> None:
        pd = self._get_personal_data()
        pd["address"] = value
        self._set_personal_data(pd)
        data = self._get_extra()
        data["address"] = value
        self._set_extra(data)

    @property
    def city_latin(self) -> Optional[str]:
        return self._get_personal_data().get("city_latin") or self._get_extra().get("city_latin")

    @city_latin.setter
    def city_latin(self, value: Optional[str]) -> None:
        pd = self._get_personal_data()
        pd["city_latin"] = value
        self._set_personal_data(pd)
        data = self._get_extra()
        data["city_latin"] = value
        self._set_extra(data)

    @property
    def address_latin(self) -> Optional[str]:
        return self._get_personal_data().get("address_latin") or self._get_extra().get("address_latin")

    @address_latin.setter
    def address_latin(self, value: Optional[str]) -> None:
        pd = self._get_personal_data()
        pd["address_latin"] = value
        self._set_personal_data(pd)
        data = self._get_extra()
        data["address_latin"] = value
        self._set_extra(data)

    @property
    def birth_date(self) -> Optional[date]:
        val = self._get_personal_data().get("birth_date")
        if val is None:
            val = self._get_extra().get("birth_date")
        if isinstance(val, str):
            try:
                return date.fromisoformat(val)
            except ValueError:
                return None
        return val

    @birth_date.setter
    def birth_date(self, value: Optional[date]) -> None:
        pd = self._get_personal_data()
        pd["birth_date"] = value.isoformat() if isinstance(value, date) else value
        self._set_personal_data(pd)
        data = self._get_extra()
        data["birth_date"] = value.isoformat() if isinstance(value, date) else value
        self._set_extra(data)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Candidate {self.id} {self.first_name} {self.last_name}>"

@event.listens_for(Candidate, "before_insert")
def assign_short_id(mapper, connection, target):
    if target.short_id:
        return

    target.short_id = next_candidate_short_id(connection)


def _max_short_numeric(connection) -> int:
    """
    Return the current max numeric part of candidate short_ids across all tenants.
    Falls back to in-Python parsing for dialects without regexp_replace (e.g. SQLite).
    """
    candidates_table = Candidate.__table__
    dialect = connection.dialect.name

    if dialect.startswith("postgres"):
        sanitized = func.nullif(
            func.regexp_replace(candidates_table.c.short_id, r"\D", "", "g"), ""
        )
        stmt = select(func.coalesce(func.max(cast(sanitized, Integer)), 0))
        result = connection.execute(stmt).scalar()
        return int(result or 0)

    # Fallback: fetch and parse short_ids manually.
    stmt = select(candidates_table.c.short_id)
    rows = connection.execute(stmt).scalars().all()
    max_numeric = 0
    for raw in rows:
        digits = "".join(ch for ch in (raw or "") if ch.isdigit())
        if digits:
            max_numeric = max(max_numeric, int(digits))
    return max_numeric


def next_candidate_short_id(connection) -> str:
    """Generate the next sequential candidate short_id as CND000001, global for all tenants."""
    next_num = _max_short_numeric(connection) + 1
    return f"CND{next_num:06d}"
