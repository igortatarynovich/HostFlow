from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .candidate import Candidate


class CandidateService(Base):
    """
    Дополнительная услуга, назначенная конкретному кандидату.
    Привязка только к кандидату (без компаний/вакансий).
    """

    __tablename__ = "candidate_services"

    # техполя
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    # ключи
    candidate_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # содержимое услуги
    service_code: Mapped[str] = mapped_column(
        String, index=True, nullable=False
    )  # машинный код услуги
    title: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # человекочитаемое название (опционально)
    price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(
        String(3), nullable=True
    )  # ISO-валюта, например "EUR"
    status: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )  # planned|in_progress|done|canceled и т.п.
    started_at: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # произвольные данные
    extra: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)

    # аудит
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # связи (при наличии модели Candidate с relationship обратным можно добавить back_populates)
    candidate = relationship("Candidate", lazy="joined", viewonly=True)
