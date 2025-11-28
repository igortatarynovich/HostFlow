from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base  # оставляем как у тебя


class Stage(Base):
    __tablename__ = "stages"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    need_work_permit: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    need_visa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    need_red_paper: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
