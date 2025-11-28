from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class CandidatePermit(Base):
    __tablename__ = "candidate_permits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    permit_type: Mapped[str] = mapped_column(String(64), nullable=False)
    number: Mapped[str] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    issued_on: Mapped[str] = mapped_column(String(32), nullable=True)
    expires_on: Mapped[str] = mapped_column(String(32), nullable=True)
    meta: Mapped[str] = mapped_column(Text, nullable=True, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class CandidateVisa(Base):
    __tablename__ = "candidate_visas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    visa_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    checkpoints: Mapped[str] = mapped_column(Text, nullable=True, default="{}")
    issued_on: Mapped[str] = mapped_column(String(32), nullable=True)
    meta: Mapped[str] = mapped_column(Text, nullable=True, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class CandidateTask(Base):
    __tablename__ = "candidate_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    due_on: Mapped[str] = mapped_column(String(32), nullable=True)
    priority: Mapped[str] = mapped_column(String(32), nullable=True)
    assigned_to: Mapped[str] = mapped_column(String(128), nullable=True)
    completed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    meta: Mapped[str] = mapped_column(Text, nullable=True, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
