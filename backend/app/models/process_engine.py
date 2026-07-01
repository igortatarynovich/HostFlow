"""Process Engine platform registry models (P1).

Canonical storage for system stages, profiles, pipelines, and rules.
Business modules register via manifests; core runtime reads these registries.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

REGISTRY_STATUS_ACTIVE = "active"
REGISTRY_STATUS_DRAFT = "draft"
REGISTRY_STATUS_ARCHIVED = "archived"
DEFAULT_REGISTRY_VERSION = "process_engine_v1"

# Empty string = platform-global catalog row (SQLite-safe unique constraint).
PLATFORM_TENANT_SCOPE = ""


class ProcessEngineRegistryMixin:
    """Shared columns for all Process Engine registry tables."""

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    module: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        default=PLATFORM_TENANT_SCOPE,
        server_default=text("''"),
        index=True,
        comment="Empty string = platform catalog; otherwise tenant-scoped row",
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    registry_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DEFAULT_REGISTRY_VERSION,
        server_default=text("'process_engine_v1'"),
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=REGISTRY_STATUS_ACTIVE,
        server_default=text("'active'"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )


class PeSystemStage(Base, TimestampMixin, ProcessEngineRegistryMixin):
    __tablename__ = "pe_system_stages"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", "code", name="uq_pe_system_stages_scope_code"),
    )

    template_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    terminal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    analytics_bucket: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


class PeStageTemplate(Base, TimestampMixin, ProcessEngineRegistryMixin):
    __tablename__ = "pe_stage_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", "code", name="uq_pe_stage_templates_scope_code"),
    )


class PeProcessProfile(Base, TimestampMixin, ProcessEngineRegistryMixin):
    __tablename__ = "pe_process_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", "code", name="uq_pe_process_profiles_scope_code"),
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    pipeline_template_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("pe_pipeline_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    legacy_candidate_profile_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("candidate_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class PePipelineTemplate(Base, TimestampMixin, ProcessEngineRegistryMixin):
    __tablename__ = "pe_pipeline_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", "code", name="uq_pe_pipeline_templates_scope_code"),
    )

    legacy_funnel_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("funnels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class PeTransitionRule(Base, TimestampMixin, ProcessEngineRegistryMixin):
    __tablename__ = "pe_transition_rules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", "code", name="uq_pe_transition_rules_scope_code"),
    )

    process_profile_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("pe_process_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default=text("100"))


class PeHandoffRule(Base, TimestampMixin, ProcessEngineRegistryMixin):
    __tablename__ = "pe_handoff_rules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", "code", name="uq_pe_handoff_rules_scope_code"),
    )

    handoff_mode: Mapped[str] = mapped_column(String(32), nullable=False)


class PeFieldRequirement(Base, TimestampMixin, ProcessEngineRegistryMixin):
    __tablename__ = "pe_field_requirements"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", "code", name="uq_pe_field_requirements_scope_code"),
    )

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)


class PeDocumentRequirement(Base, TimestampMixin, ProcessEngineRegistryMixin):
    __tablename__ = "pe_document_requirements"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", "code", name="uq_pe_document_requirements_scope_code"),
    )

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)


class PeOverrideRule(Base, TimestampMixin, ProcessEngineRegistryMixin):
    __tablename__ = "pe_override_rules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", "code", name="uq_pe_override_rules_scope_code"),
    )

    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="both", server_default=text("'both'"))


__all__ = [
    "DEFAULT_REGISTRY_VERSION",
    "PLATFORM_TENANT_SCOPE",
    "REGISTRY_STATUS_ACTIVE",
    "REGISTRY_STATUS_ARCHIVED",
    "REGISTRY_STATUS_DRAFT",
    "PeDocumentRequirement",
    "PeFieldRequirement",
    "PeHandoffRule",
    "PeOverrideRule",
    "PePipelineTemplate",
    "PeProcessProfile",
    "PeStageTemplate",
    "PeSystemStage",
    "PeTransitionRule",
]
