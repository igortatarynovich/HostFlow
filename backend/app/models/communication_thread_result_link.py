"""Communication Thread ↔ opaque destination result link (C1).

Communications-owned. Stores OpaqueResultRef only — no FK to Application /
SalesInquiry ORM tables. Provenance points at Flights ledger id (soft string).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base

from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

LINK_STATUS_CONFIRMED = "confirmed"
LINK_STATUS_UNRESOLVED = "unresolved"


class CommunicationThreadResultLink(Base, TimestampMixin):
    """Primary Thread → opaque result reference (Communication Context C1)."""

    __tablename__ = "communication_thread_result_links"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "thread_id",
            name="uq_comm_thread_result_links_tenant_thread",
        ),
        Index(
            "ix_comm_thread_result_links_tenant_result",
            "tenant_id",
            "module_owner",
            "result_type",
            "result_id",
        ),
        Index(
            "ix_comm_thread_result_links_tenant_ledger",
            "tenant_id",
            "ledger_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # OpaqueResultRef — never typed FK into destination domain tables.
    module_owner: Mapped[str] = mapped_column(String(32), nullable=False)
    result_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # Soft Flights provenance reference (acq_flight_dispatch_ledger.id).
    ledger_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'confirmed'"),
        default=LINK_STATUS_CONFIRMED,
    )
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True, default=dict)
