"""Recruitment Application — intent layer (MVP). See docs/specs/workflows/application-creation-mvp.md.

Do not assign ``status`` directly from services — use
``backend.app.services.recruitment_application_lifecycle.set_recruitment_application_status``
so transitions and legacy ``active`` normalization stay consistent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base

from .mixins import TimestampMixin, now_utc

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class RecruitmentApplication(Base, TimestampMixin):
    __tablename__ = "recruitment_applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    lead_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vacancy_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("vacancies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("'meta'"), default="meta")
    recruiter_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'applied'"),
        default="applied",
        index=True,
    )
    application_cycle: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True, default=dict)
