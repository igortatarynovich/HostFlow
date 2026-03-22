from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin


class CandidatePipelineOverride(TimestampMixin, Base):
    """
    Recruiter requests waiving document pipeline/handoff blockers for a checklist doc type.
    Manager/admin approves with scope: pipeline-only or including ready_for_handoff gate.
    """

    __tablename__ = "candidate_pipeline_overrides"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    doc_type_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # pending | approved | rejected | revoked
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Recruiter asks: relax pipeline only, or also request handoff inclusion (needs manager grant).
    requested_scope: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'pipeline'")
    )
    # Set on approve: pipeline | both
    granted_scope: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    requested_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
