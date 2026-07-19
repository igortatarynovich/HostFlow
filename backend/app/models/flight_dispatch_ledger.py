"""Flights dispatch provenance ledger (Intake Runtime Split R5).

Acquisition-owned. Stores opaque destination result references only —
never typed FKs into Recruitment Application / SalesInquiry tables.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

STATUS_PENDING = "pending"
STATUS_DISPATCHED = "dispatched"
STATUS_CONFIRMED = "confirmed"
STATUS_FAILED = "failed"
STATUS_UNRESOLVED = "unresolved"


class FlightDispatchLedger(Base, TimestampMixin):
    """Flights-owned dispatch decision + opaque result provenance."""

    __tablename__ = "acq_flight_dispatch_ledger"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_acq_flight_dispatch_ledger_tenant_idempotency",
        ),
        Index("ix_acq_flight_dispatch_ledger_tenant_status", "tenant_id", "status"),
        Index(
            "ix_acq_flight_dispatch_ledger_tenant_transport",
            "tenant_id",
            "transport_lead_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Flights / handoff scoped — not Application.id / SalesInquiry.id.
    idempotency_key: Mapped[str] = mapped_column(String(191), nullable=False)
    handoff_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    transport_lead_id: Mapped[str] = mapped_column(String(36), nullable=False)

    route_intent: Mapped[str] = mapped_column(String(64), nullable=False)
    destination: Mapped[str] = mapped_column(String(32), nullable=False)
    dispatcher_id: Mapped[str] = mapped_column(String(128), nullable=False)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text(f"'{STATUS_PENDING}'"),
        default=STATUS_PENDING,
    )

    # Opaque destination reference (populated on confirm).
    module_owner: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    result_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    result_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    failure_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True, default=dict)

    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
