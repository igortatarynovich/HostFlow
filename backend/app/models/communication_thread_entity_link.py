"""G13: Communication Thread ↔ origin entity links.

Communications-owned durable binding. Distinct from C1 Thread Result Link
(opaque Sales/Recruitment result for policy). Multiple entity links per thread
are allowed (e.g. sales_inquiry + transport lead).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class CommunicationThreadEntityLink(Base):
    """Durable thread ↔ HostFlow origin entity (G13)."""

    __tablename__ = "communication_thread_entity_links"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "thread_id",
            "entity_type",
            "entity_id",
            name="uq_comm_thread_entity_link",
        ),
        Index(
            "ix_comm_thread_links_tenant_entity",
            "tenant_id",
            "entity_type",
            "entity_id",
        ),
        Index(
            "ix_comm_thread_links_tenant_thread",
            "tenant_id",
            "thread_id",
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
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    is_immutable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
