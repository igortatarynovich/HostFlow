"""Model for tracking candidate profile change history."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from backend.app.db.base import Base
from .mixins import now_utc

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class CandidateProfileHistory(Base):
    """История изменений профиля кандидата.
    
    Отслеживает все изменения профиля (конфигурации полей, этапов, документов).
    """

    __tablename__ = "candidate_profile_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Действие: 'created', 'updated', 'deleted', 'activated', 'deactivated'"
    )
    
    # Снапшот профиля до изменения (для diff)
    old_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True, comment="Данные профиля до изменения"
    )
    
    # Снапшот профиля после изменения
    new_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True, comment="Данные профиля после изменения"
    )
    
    # Детали изменений (какие поля изменились)
    changes: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True, comment="Детали изменений (diff)"
    )
    
    comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Комментарий к изменению")
    
    # Кто инициировал изменение
    actor_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID пользователя, который внес изменение"
    )
    actor_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Имя пользователя (для отображения)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )


__all__ = ["CandidateProfileHistory"]
