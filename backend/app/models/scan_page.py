from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import ScanPageStatus


class ScanPage(Base):
    __tablename__ = "scan_pages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scan_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_code: Mapped[str] = mapped_column(String(64), nullable=False)
    page_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    original_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    processed_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    status: Mapped[ScanPageStatus] = mapped_column(
        Enum(ScanPageStatus, name="scan_page_status_enum"),
        nullable=False,
        default=ScanPageStatus.pending,
    )
    rotation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applied_filter: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    issues: Mapped[list[str] | None] = mapped_column(
        MutableList.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
        default=list,
    )
    meta: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    session = relationship("ScanSession", back_populates="pages")
