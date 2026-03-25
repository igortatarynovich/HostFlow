"""Persisted risk intelligence v1 aggregates (Phase B shadow / hourly trends)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, Integer, String, text
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import now_utc

JSONType = JSON().with_variant(JSONB, "postgresql")


class RiskIntelTenantHourly(Base):
    """One aggregate row per tenant per UTC hour (scheduler or backfill)."""

    __tablename__ = "risk_intel_tenant_hourly"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    risk_version: Mapped[str] = mapped_column(String(32), nullable=False, default="risk_model_v1")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=text("CURRENT_TIMESTAMP")
    )
    candidates_evaluated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    high_risk_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    band_low: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    band_medium: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    band_high: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    band_critical: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_response_histogram: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    effective_weights: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


class RiskIntelEntityShadow(Base):
    """Shadow scoring rows for high/critical candidates (audit + validation cohorts)."""

    __tablename__ = "risk_intel_entity_shadow"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, default="candidate")
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    risk_version: Mapped[str] = mapped_column(String(32), nullable=False, default="risk_model_v1")
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    band: Mapped[str] = mapped_column(String(16), nullable=False)
    stage_at_score: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    drivers: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
