from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def now_utc() -> datetime:
    return datetime.utcnow()


class ClientAccount(Base):
    __tablename__ = "client_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    own_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        index=True,
        nullable=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="prospect",
        server_default=text("'prospect'"),
    )
    owner_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        index=True,
        nullable=True,
    )
    primary_contact_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    primary_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        index=True,
        nullable=True,
    )
    source_lead_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=now_utc,
    )

    __table_args__ = (
        Index("ix_client_accounts_tenant_status", "tenant_id", "status"),
        Index("ix_client_accounts_tenant_display_name", "tenant_id", "display_name"),
    )
