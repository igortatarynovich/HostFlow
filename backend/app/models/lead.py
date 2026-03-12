from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
    text,
    Boolean,
    Integer,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import now_utc, TimestampMixin


JSONType = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))
JSONAnyType = SQLiteJSON().with_variant(JSONB, "postgresql")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    company_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    vacancy_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("vacancies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="meta",
        server_default=text("'meta'"),
    )
    ad_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    normalized: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="new",
        server_default=text("'new'"),
        index=True,
    )
    stage: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )
    funnel_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("funnels.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    candidate_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_routed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class MetaAdsMap(Base):
    __tablename__ = "meta_ads_map"

    ad_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    vacancy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class MetaLeadCredential(TimestampMixin, Base):
    __tablename__ = "meta_lead_credentials"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=text("'active'"),
        index=True,
    )
    encrypted_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted_ad_account_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted_page_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_rotation_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class MetaLeadSettings(TimestampMixin, Base):
    __tablename__ = "meta_lead_settings"

    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    default_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    fallback_recruiter_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    auto_create_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    reroute_after_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mask_pii_in_logs: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    pull_field_data_from_graph: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    field_mapping: Mapped[list] = mapped_column(
        JSONAnyType,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    webhook_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_webhook_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_signature_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    webhook_verify_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
