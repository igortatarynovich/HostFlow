"""Models for process templates (шаблоны процессов документов)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from backend.app.db.base import Base
from .enums import DocumentStatusModel
from .mixins import TimestampMixin


class ProcessTemplate(Base, TimestampMixin):
    """Шаблон процесса документа.

    Определяет:
    - Статусы и разрешённые переходы
    - Шаги процесса (PREPARE, SUBMIT, WAIT, DECISION, etc.)
    - Обязательные поля для каждого шага
    - Обязательные файлы для каждого шага
    - SLA и напоминания
    - Автологику (например, авто-переход в EXPIRED)

    Примеры: TPL_WP_A, TPL_OSW, TPL_RESIDENCE
    """

    __tablename__ = "process_templates"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_process_template_tenant_code",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    code: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="Код шаблона (например, 'TPL_WP_A', 'TPL_OSW')"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Статус-модель, к которой относится этот шаблон
    status_model: Mapped[DocumentStatusModel] = mapped_column(
        sa.Enum(DocumentStatusModel, name="document_status_model_enum", native_enum=False),
        nullable=False,
    )

    # Конфигурация шаблона (JSONB)
    # Формат:
    # {
    #   "statuses": {
    #     "MISSING": {"label": "Отсутствует", "is_terminal": false},
    #     "UPLOADED": {"label": "Загружен", "is_terminal": false},
    #     "VERIFIED": {"label": "Проверен", "is_terminal": false, "is_ok": true},
    #     "EXPIRED": {"label": "Истёк", "is_terminal": false},
    #     "REJECTED": {"label": "Отклонён", "is_terminal": false}
    #   },
    #   "transitions": [
    #     {"from": "MISSING", "to": "UPLOADED", "allowed": true},
    #     {"from": "UPLOADED", "to": "VERIFIED", "allowed": true},
    #     {"from": "UPLOADED", "to": "REJECTED", "allowed": true},
    #     ...
    #   ],
    #   "steps": [
    #     {
    #       "step_code": "PREPARE",
    #       "name": "Подготовка",
    #       "entry_status": "TO_PREPARE",
    #       "required_fields": ["responsible_user_id"],
    #       "optional_fields": ["case_number"],
    #       "required_files": [],
    #       "optional_files": ["APPLICATION_SET"],
    #       "sla_days": 7,
    #       "reminders": [
    #         {"days_after": 3, "message": "Напоминание о подготовке"}
    #       ]
    #     },
    #     {
    #       "step_code": "SUBMIT",
    #       "name": "Подача",
    #       "entry_status": "SUBMITTED",
    #       "required_fields": ["submitted_at"],
    #       "required_files": ["SUBMISSION_CONFIRMATION"],
    #       "sla_days": 3,
    #       "auto_transition_from": "TO_PREPARE"
    #     },
    #     ...
    #   ],
    #   "auto_logic": {
    #     "expire_on_valid_to": true,
    #     "expire_status": "EXPIRED",
    #     "is_valid_check": "valid_to >= today"
    #   },
    #   "ok_conditions": {
    #     "for_gates": [
    #       {"status": "VERIFIED", "is_valid": true}
    #     ]
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
        comment="Системный шаблон (нельзя удалить/изменить основные правила)",
    )

    # Порядок отображения
    order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )


__all__ = ["ProcessTemplate"]

