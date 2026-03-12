"""Per-tenant email (SMTP) configuration."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import now_utc


class TenantEmailConfig(Base):
    """SMTP configuration for tenant. One config per tenant."""

    __tablename__ = "tenant_email_config"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False, default="smtp", server_default="smtp"
    )
    smtp_host: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    smtp_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, server_default=text("587"))
    smtp_user: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    smtp_password_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    from_email: Mapped[str] = mapped_column(String(256), nullable=False)
    from_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    use_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
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
    )
