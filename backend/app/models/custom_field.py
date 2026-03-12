from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from backend.app.db.base import Base
from .mixins import TimestampMixin


class CustomFieldScope(str, Enum):
    """Где живёт поле: на кандидате целиком или внутри конкретного типа документа."""

    CANDIDATE = "candidate"
    DOCUMENT = "document"


class CustomFieldEntityType(str, Enum):
    """К какому типу сущности привязано значение поля."""

    CANDIDATE = "candidate"
    CANDIDATE_DOCUMENT = "candidate_document"


class CustomFieldType(str, Enum):
    """Тип значения кастомного поля."""

    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    CHECKBOX = "checkbox"
    SELECT = "select"
    MULTISELECT = "multiselect"


class CustomFieldDefinition(Base, TimestampMixin):
    """Описание кастомного поля, настраиваемого тенантом."""

    __tablename__ = "custom_field_definitions"
    __table_args__ = (
        # Уникальность ключа в рамках тенанта/скоупа/типа документа.
        sa.UniqueConstraint(
            "tenant_id",
            "scope",
            "document_type_id",
            "key",
            name="uq_custom_field_key_per_document",
        ),
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

    scope: Mapped[CustomFieldScope] = mapped_column(
        SAEnum(CustomFieldScope, name="custom_field_scope_enum", native_enum=False),
        nullable=False,
    )

    # Для DOCUMENT-скоупа указывает, к какому DocumentType относится поле.
    document_type_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("document_types.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    field_type: Mapped[CustomFieldType] = mapped_column(
        SAEnum(CustomFieldType, name="custom_field_type_enum", native_enum=False),
        nullable=False,
    )

    required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    # Опции для select/multiselect (список значений).
    options: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
    )

    help_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )
    # System fields are immutable in tenant UI/API and act as a stable schema skeleton.
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )


class CustomFieldValue(Base, TimestampMixin):
    """Значение кастомного поля для конкретной сущности."""

    __tablename__ = "custom_field_values"
    __table_args__ = (
        sa.UniqueConstraint(
            "tenant_id",
            "definition_id",
            "entity_type",
            "entity_id",
            name="uq_custom_field_value_entity",
        ),
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

    definition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("custom_field_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    entity_type: Mapped[CustomFieldEntityType] = mapped_column(
        SAEnum(CustomFieldEntityType, name="custom_field_entity_type_enum", native_enum=False),
        nullable=False,
    )

    entity_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    # Значение храним в jsonb, валидация и приведение типов — в приложении.
    value: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )

    updated_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    definition: Mapped[CustomFieldDefinition] = relationship(
        CustomFieldDefinition,
        backref="values",
    )


__all__ = [
    "CustomFieldScope",
    "CustomFieldEntityType",
    "CustomFieldType",
    "CustomFieldDefinition",
    "CustomFieldValue",
]
