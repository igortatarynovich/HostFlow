"""Models for document policies (tenant/client/vacancy-level document requirements)."""

from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from backend.app.db.base import Base
from .enums import GateCode, RequirementType
from .mixins import TimestampMixin


class DocumentPolicyScope(str, Enum):
    """Уровень, на котором задаётся политика документа.

    Приоритет разрешения конфликтов:
    VACANCY > CLIENT > TENANT.
    """

    TENANT = "tenant"
    CLIENT = "client"
    VACANCY = "vacancy"


class RequirementLevel(str, Enum):
    """Уровень требования (насколько критично)."""

    DISABLED = "disabled"  # Требование отключено
    OPTIONAL = "optional"  # Опционально (не блокирует)
    REQUIRED = "required"  # Обязательно (блокирует gate)
    BLOCKING = "blocking"  # Критично (жёстко блокирует gate)


class DocumentPolicy(Base, TimestampMixin):
    """Политика документа или требования.

    Может ссылаться на:
    - document_type_id (конкретный тип документа)
    - requirement_code (виртуальное требование, например CODE95_EVIDENCE)

    Применяется на определённых gates (этапах).
    """

    __tablename__ = "document_policies"
    __table_args__ = (
        # Проверка: либо document_type_id, либо requirement_code должен быть задан
        sa.CheckConstraint(
            "(document_type_id IS NOT NULL AND requirement_code IS NULL) OR "
            "(document_type_id IS NULL AND requirement_code IS NOT NULL)",
            name="ck_document_policy_type_or_requirement",
        ),
        # Примечание: частичные уникальные индексы создаются в миграции через op.execute,
        # так как UniqueConstraint не поддерживает postgresql_where напрямую
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    own_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    scope: Mapped[DocumentPolicyScope] = mapped_column(
        SAEnum(DocumentPolicyScope, name="document_policy_scope_enum", native_enum=False),
        nullable=False,
    )

    # Для TENANT scope_id = NULL, для CLIENT/VACANCY = id клиента/вакансии.
    scope_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Либо document_type_id, либо requirement_code (но не оба одновременно)
    document_type_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("document_types.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    requirement_code: Mapped[Optional[RequirementType]] = mapped_column(
        SAEnum(RequirementType, name="requirement_type_enum", native_enum=False),
        nullable=True,
        index=True,
    )

    # Уровень требования
    required_level: Mapped[RequirementLevel] = mapped_column(
        SAEnum(RequirementLevel, name="requirement_level_enum", native_enum=False),
        nullable=False,
        default=RequirementLevel.REQUIRED,
        server_default=text("'required'"),
    )

    # Gates, на которых это требование применяется (список gate_code)
    _JSONList = MutableList.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))
    gates: Mapped[list[str]] = mapped_column(
        _JSONList,
        nullable=False,
        default=list,
        comment="Список gate_code, на которых применяется это требование",
    )

    # Включён ли документ/требование в принципе для этого scope.
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("1"),
        default=True,
    )

    # За сколько дней до истечения начинать напоминать (если есть expiry).
    alert_days_before_expiry: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Ответственный пользователь (опционально).
    # Phase 2.6.G-5 Stage E — FK ``users.id ON DELETE SET NULL`` added via
    # Alembic ``202604190002_owner_fk_set_null``. Index on the same
    # revision (``ix_document_policies_owner_user_id``) speeds up both
    # the ``?owner=<user>`` filter in the admin view and the on-delete
    # NULL-sweep performed by the FK trigger.
    owner_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


__all__ = ["DocumentPolicy", "DocumentPolicyScope", "RequirementLevel"]
