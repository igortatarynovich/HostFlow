from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class RefDocumentType(Base):
    __tablename__ = "ref_document_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    public_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default=text("'draft'"), index=True)
    origin: Mapped[str] = mapped_column(String(24), nullable=False, default="system", server_default=text("'system'"), index=True)
    category_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subcategory_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    criticality: Mapped[str] = mapped_column(String(32), nullable=False, default="informational", server_default=text("'informational'"), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class RefDocumentTypeI18n(Base):
    __tablename__ = "ref_document_type_i18n"
    __table_args__ = (
        UniqueConstraint("document_type_id", "locale", name="uq_ref_document_type_i18n_doc_locale"),
    )

    _JSONList = MutableList.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("ref_document_types.id", ondelete="CASCADE"), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    public_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(_JSONList, nullable=False, default=list, server_default=text("'[]'"))


class RefDocumentTypeVersion(Base):
    __tablename__ = "ref_document_type_versions"
    __table_args__ = (
        UniqueConstraint("document_type_id", "version_code", name="uq_ref_document_type_versions_doc_ver"),
    )

    _JSONDict = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("ref_document_types.id", ondelete="CASCADE"), nullable=False, index=True)
    version_code: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    deprecation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    replacement_document_type_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("ref_document_types.id", ondelete="SET NULL"), nullable=True, index=True)

    schema_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    expiry_rules_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    automation_flags_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    verification_profile_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    stage_applicability_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    position_applicability_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    entity_applicability_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    business_purposes_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))

    status_model: Mapped[str] = mapped_column(String(32), nullable=False, default="evidence", server_default=text("'evidence'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class RefDocumentTypeCountryApplicability(Base):
    __tablename__ = "ref_document_type_country_applicability"

    _JSONList = MutableList.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))
    _JSONDict = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_type_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("ref_document_type_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    applicability_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="global", server_default=text("'global'"), index=True)
    country_codes: Mapped[list[str]] = mapped_column(_JSONList, nullable=False, default=list, server_default=text("'[]'"))
    country_group_codes: Mapped[list[str]] = mapped_column(_JSONList, nullable=False, default=list, server_default=text("'[]'"))
    issuing_country_rules_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    work_country_rules_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    residence_country_rules_json: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))


class RefDocumentTypeRequest(Base):
    __tablename__ = "tenant_document_type_requests"

    _JSONDict = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requested_code: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_payload: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="requested", server_default=text("'requested'"), index=True)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TenantDocumentTypeOverride(Base):
    __tablename__ = "tenant_document_type_overrides"

    _JSONDict = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("ref_document_types.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(24), nullable=False)
    scope_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    enabled: Mapped[Optional[bool]] = mapped_column(nullable=True)
    required_level: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    alert_days_before_expiry: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    responsible_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    internal_instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_specific_requirement_json: Mapped[Optional[dict[str, Any]]] = mapped_column(_JSONDict, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))


class RefPack(Base):
    __tablename__ = "ref_packs"

    _JSONDict = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, index=True)
    industry_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default=text("'draft'"), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))


class RefPackItem(Base):
    __tablename__ = "ref_pack_items"
    __table_args__ = (
        UniqueConstraint("pack_id", "document_type_version_id", name="uq_ref_pack_items_pack_doc_ver"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pack_id: Mapped[str] = mapped_column(String(36), ForeignKey("ref_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("ref_document_type_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(24), nullable=False)


class RefPackRule(Base):
    __tablename__ = "ref_pack_rules"

    _JSONDict = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pack_id: Mapped[str] = mapped_column(String(36), ForeignKey("ref_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default=text("100"))
    condition_expr: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))
    effect_type: Mapped[str] = mapped_column(String(64), nullable=False)
    effect_payload: Mapped[dict[str, Any]] = mapped_column(_JSONDict, nullable=False, default=dict, server_default=text("'{}'"))


class TenantDocumentPackEnablement(Base):
    __tablename__ = "tenant_document_pack_enablements"
    __table_args__ = (
        UniqueConstraint("tenant_id", "pack_id", name="uq_tenant_document_pack_enablements_tenant_pack"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pack_id: Mapped[str] = mapped_column(String(36), ForeignKey("ref_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=func.true())
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
