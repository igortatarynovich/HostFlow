# app/models/_mixins.py
from sqlalchemy import DateTime, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class TimestampMixin:
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=func.now(),
        nullable=False,
    )
