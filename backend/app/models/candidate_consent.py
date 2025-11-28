from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import now_utc

JSONType = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))


class CandidateConsent(Base):
  __tablename__ = "candidate_consents"

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
  tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
  candidate_id: Mapped[str] = mapped_column(
      String(36),
      ForeignKey("candidates.id", ondelete="CASCADE"),
      index=True,
      nullable=False,
  )
  consent_code: Mapped[str] = mapped_column(String(64), nullable=False)
  text_version: Mapped[str] = mapped_column(String(32), nullable=False)
  accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
  user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
  payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True, default=dict)
  accepted_at: Mapped[datetime] = mapped_column(
      DateTime(timezone=True),
      default=now_utc,
      server_default=text("CURRENT_TIMESTAMP"),
      nullable=False,
  )
  created_at: Mapped[datetime] = mapped_column(
      DateTime(timezone=True),
      default=now_utc,
      server_default=text("CURRENT_TIMESTAMP"),
      nullable=False,
  )
