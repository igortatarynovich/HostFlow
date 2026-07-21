"""ADR-024 Stage 3E PR-1 — Acquisition Activity Timeline (append-only).

``AcquisitionActivityEvent`` is the durable audit projection for the inbound
demand flow. It is **not** an Automation queue and not a Flight-owned journal.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

ACTOR_TYPE_USER = "user"
ACTOR_TYPE_SYSTEM = "system"
ACTOR_TYPE_AUTOMATION = "automation"
ACTOR_TYPE_PROVIDER = "provider"

ACTOR_TYPES = frozenset(
    {
        ACTOR_TYPE_USER,
        ACTOR_TYPE_SYSTEM,
        ACTOR_TYPE_AUTOMATION,
        ACTOR_TYPE_PROVIDER,
    }
)


class AcquisitionActivityEvent(Base):
    """Immutable Acquisition activity row (append-only).

    No ``updated_at`` — corrections are new events. FKs stay inside Acquisition
    ownership (Campaign / Flight / Outcome). Endpoint / Submission / Result ids
    and Lead/Candidate refs are opaque strings (payload or nullable columns).
    """

    __tablename__ = "acquisition_activity_events"
    __table_args__ = (
        Index(
            "ix_acq_act_ev_tenant_campaign_occurred",
            "tenant_id",
            "campaign_id",
            "occurred_at",
            "id",
        ),
        Index(
            "ix_acq_act_ev_tenant_flight_occurred",
            "tenant_id",
            "flight_id",
            "occurred_at",
            "id",
        ),
        Index(
            "ix_acq_act_ev_tenant_submission_occurred",
            "tenant_id",
            "submission_id",
            "occurred_at",
        ),
        Index(
            "ix_acq_act_ev_tenant_type_occurred",
            "tenant_id",
            "event_type",
            "occurred_at",
        ),
        Index(
            "uq_acq_act_ev_tenant_source_event",
            "tenant_id",
            "source_event_id",
            unique=True,
            sqlite_where=text("source_event_id IS NOT NULL"),
            postgresql_where=text("source_event_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flight_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("acq_campaign_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Opaque Endpoint identity (V1: Form / Intake Source / future unified Endpoint).
    endpoint_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Opaque intake submission identity (no FK outside Acquisition).
    submission_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    # Opaque Result identity (result_type lives in payload when needed).
    result_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Acquisition Outcome id (opaque string — no FK so parent deletes cannot mutate rows).
    outcome_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_version: Mapped[str] = mapped_column(String(16), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    source_event_id: Mapped[Optional[str]] = mapped_column(String(191), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    causation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


__all__ = [
    "AcquisitionActivityEvent",
    "ACTOR_TYPE_USER",
    "ACTOR_TYPE_SYSTEM",
    "ACTOR_TYPE_AUTOMATION",
    "ACTOR_TYPE_PROVIDER",
    "ACTOR_TYPES",
]
