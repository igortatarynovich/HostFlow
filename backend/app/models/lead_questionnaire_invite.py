from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

# Relative Base import (not backend.app.db.base): under the uvicorn /app/backend
# symlink an absolute import can load a second Base and break FKs to tenant_lead_forms.
# app.db.base also aliases backend.app.db.base so Lead (absolute Base import) shares MetaData.
from ..db.base import Base

# Ensure FK targets are registered in the same MetaData (SQLAlchemy NoReferencedTableError).
from .lead import Lead  # noqa: F401
from .tenant_lead_form import TenantLeadForm  # noqa: F401

JSONType = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))


class LeadQuestionnaireInvite(Base):
    __tablename__ = "lead_questionnaire_invites"
    __table_args__ = (
        Index("ix_lead_questionnaire_invites_lead_id", "lead_id"),
        Index("ix_lead_questionnaire_invites_token", "token", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    lead_form_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenant_lead_forms.id", ondelete="SET NULL"), nullable=True)
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_sent")
    entity_profile_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    presentation_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    apply_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
