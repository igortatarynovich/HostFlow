"""Models for candidate profiles (конфигурация полей и требований для вакансии)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from backend.app.db.base import Base
from .mixins import TimestampMixin


class CandidateProfile(Base, TimestampMixin):
    """Профиль кандидата для вакансии.

    Определяет:
    - Какие поля отображать в карточке кандидата
    - Какие документы требуются
    - Какие gates применяются
    - Кастомные поля (через CustomFieldDefinition)
    - Политики документов (через DocumentPolicy)

    Один профиль может быть привязан к одной или нескольким вакансиям.
    """

    __tablename__ = "candidate_profiles"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_candidate_profile_tenant_code",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    code: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="Уникальный код профиля (например, 'driver_ce' или 'warehouse_worker')"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Привязка к клиенту (опционально, если профиль специфичен для клиента)
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Воронка (этапы) — ссылка на Funnel. Если задана, этапы берутся из воронки, не из config.
    funnel_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True, comment="FK to funnels.id"
    )

    # Конфигурация профиля (JSONB)
    # Формат:
    # {
    #   "required_fields": ["first_name", "last_name", "phone", "email", ...],
    #   "optional_fields": ["middle_name", "address", ...],
    #   "document_requirements": [
    #     {"document_type": "PASSPORT", "required_level": "BLOCKING", "gates": ["GATE_DOCS_RECEIVED"]},
    #     ...
    #   ],
    #   "custom_fields": ["custom_field_definition_id_1", ...],
    #   "gates": ["GATE_DOCS_RECEIVED", "GATE_ON_CLIENT_BASE", "GATE_ON_ROUTE"],
    #   "settings": {
    #     "allow_manual_status_change": true,
    #     "auto_expire_documents": true,
    #     ...
    #   }
    # }
    config: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
        comment="Системный профиль (нельзя удалить/изменить основные поля)",
    )

    # Ответственный пользователь
    # Phase 2.6.G-5 Stage E — FK ``users.id ON DELETE SET NULL`` added via
    # Alembic ``202604190002_owner_fk_set_null``. Index on the same
    # revision (``ix_candidate_profiles_owner_user_id``) speeds up both
    # the ``?owner=<user>`` filter in the admin view and the on-delete
    # NULL-sweep performed by the FK trigger.
    owner_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Метаданные
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


__all__ = ["CandidateProfile"]

