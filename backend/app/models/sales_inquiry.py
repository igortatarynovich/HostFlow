"""Sales Inquiry — destination result object (Intake Runtime Split R4).

Independent of Lead. Lead may remain optional transport/compatibility only.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

INITIAL_SALES_INQUIRY_STATUS = "received"


class SalesInquiry(Base, TimestampMixin):
    __tablename__ = "sales_inquiries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    # Optional legacy transport — immutable link after successful routing.
    lead_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'received'"),
        default=INITIAL_SALES_INQUIRY_STATUS,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("'public_intake'"), default="public_intake")
    own_company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entity_profile_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    intake_source_profile_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    form_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(191), nullable=True, index=True)
    # Free-form provenance stamps until R5 ledger.
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True, default=dict)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
