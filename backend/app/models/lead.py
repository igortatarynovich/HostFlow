from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
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
from backend.app.db.tsvector_compat import TsVector
from .mixins import now_utc, TimestampMixin


JSONType = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))
JSONAnyType = SQLiteJSON().with_variant(JSONB, "postgresql")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    own_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("own_companies.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    lead_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="candidate",
        server_default=text("'candidate'"),
    )
    lead_target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="candidate",
        server_default=text("'candidate'"),
    )
    company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=True,
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
    hostflow_lead_json_tsv: Mapped[Optional[Any]] = mapped_column(TsVector, nullable=True)
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
    # §2.10 / §2.3: Manual / Assisted / Automatic (ingest + normalized stamp; automatic needs Team plan at runtime).
    leads_processing_mode_v1: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    # §2.4: when Automatic + auto_create_enabled, actually create candidate on fit only if True (safeguard).
    leads_auto_convert_on_fit_v1: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    # §2.11: path secret for POST /api/v1/public/leads/inbound/{secret} (Team+); unique when set.
    generic_inbound_webhook_secret: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class MetaFormRoute(TimestampMixin, Base):
    """Intake route: Meta form → OwnCompany profile → lead_target_type → pipeline."""

    __tablename__ = "meta_form_routes"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="meta",
        server_default=text("'meta'"),
    )
    page_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    form_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    own_company_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("own_companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    lead_target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="candidate",
        server_default=text("'candidate'"),
    )
    pipeline_preset: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    default_assignee_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class MetaLeadFormMapping(TimestampMixin, Base):
    """Per Meta lead form field-mapping rules (PR-2); falls back to MetaLeadSettings.field_mapping when absent."""

    __tablename__ = "meta_lead_form_mappings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="meta",
        server_default=text("'meta'"),
    )
    page_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    form_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    form_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mapping_rules: Mapped[list] = mapped_column(
        JSONAnyType,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    last_sample_lead_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class MetaOAuthPending(Base):
    """Short-lived row: encrypted page tokens after Facebook Login (Meta Leads OAuth)."""

    __tablename__ = "meta_oauth_pending"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
