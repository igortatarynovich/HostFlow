from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, text
from sqlalchemy.orm import Mapped, mapped_column


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """
    Единый миксин для таймстемпов.
    ДАЁМ и client-side default (Python), и server_default (DB) — чтобы INSERT
    проходил даже если ORM не подставил значения.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,  # client-side
        server_default=text("CURRENT_TIMESTAMP"),  # server-side
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,  # client-side
        onupdate=now_utc,  # client-side onupdate
        server_default=text("CURRENT_TIMESTAMP"),  # server-side (первичная)
        # server_onupdate для SQLite нет, поэтому подстраховываемся onupdate=...
    )
