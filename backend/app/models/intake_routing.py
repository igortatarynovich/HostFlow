"""Intake Routing Foundation — canonical source profiles and provider bindings (PR-2)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base
from .intake_routing_enums import (
    IntakeChannel,
    IntakeProvider,
    RouteIntent,
)

from .mixins import TimestampMixin

JSONAnyType = SQLiteJSON().with_variant(JSONB, "postgresql")


class IntakeSourceProfile(Base, TimestampMixin):
    """Tenant-scoped intake entry point configuration (reference layer)."""

    __tablename__ = "intake_source_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_intake_source_profiles_tenant_code"),
        UniqueConstraint("public_slug", name="uq_intake_source_profiles_public_slug"),
        Index("ix_intake_source_profiles_tenant_active", "tenant_id", "is_active"),
        Index("ix_intake_source_profiles_public_slug", "public_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=IntakeProvider.unknown.value,
    )
    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=IntakeChannel.unknown.value,
    )
    own_company_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    route_intent: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RouteIntent.unknown.value,
    )
    pipeline_preset: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    public_slug: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    form_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lead_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    lead_target_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    entity_profile_code: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="Entity Profile Definition Registry code (P2 bridge)",
    )
    presentation_code: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="Form Presentation Runtime code bound to this intake source (P8)",
    )
    mapping_rules: Mapped[list[Any]] = mapped_column(
        JSONAnyType,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
        comment="Provider field → qualified_code mapping rules (P9)",
    )
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    default_assignee_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )
    default_language: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    supported_languages: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publication_config_v1: Mapped[dict] = mapped_column(
        JSONAnyType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
        comment="ADR-022 publication attribution and limited policy overrides",
    )


class IntakeSourceBinding(Base, TimestampMixin):
    """Maps external provider key → IntakeSourceProfile."""

    __tablename__ = "intake_source_bindings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            "external_key",
            "external_key_secondary",
            name="uq_intake_source_bindings_tenant_provider_keys",
        ),
        Index("ix_intake_source_bindings_profile", "intake_source_profile_id"),
        Index("ix_intake_source_bindings_tenant_provider", "tenant_id", "provider"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False,
    )
    intake_source_profile_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_key: Mapped[str] = mapped_column(String(255), nullable=False)
    external_key_secondary: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


__all__ = [
    "IntakeSourceProfile",
    "IntakeSourceBinding",
]
