from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class CandidateStageHistory(Base):
    __tablename__ = "candidate_stage_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), index=True)

    from_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_code: Mapped[str] = mapped_column(
        String(64), ForeignKey("stages.code"), nullable=False
    )

    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)

    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
