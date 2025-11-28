from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import ScanSessionStatus
from .candidate import Candidate


class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(Candidate.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(128), nullable=False)
    document_kind_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    preset_code: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[ScanSessionStatus] = mapped_column(
        Enum(ScanSessionStatus, name="scan_session_status_enum"),
        nullable=False,
        default=ScanSessionStatus.in_progress,
    )
    expected_pages: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=False,
        default=list,
    )
    meta: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
        default=dict,
    )
    quality_summary: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
        default=dict,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    pages = relationship(
        "ScanPage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ScanPage.created_at",
    )
