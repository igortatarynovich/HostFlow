"""Field Registry & Card Layout platform models (P1).

Canonical field definitions and card layout profiles live in Platform Core.
Business modules register via manifests; runtime reads these registries (P1: read-only).
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
DEFAULT_REGISTRY_VERSION = "field_registry_v1"

PLATFORM_TENANT_SCOPE = ""


class FieldRegistryMixin:
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
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    registry_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DEFAULT_REGISTRY_VERSION,
        server_default=text("'field_registry_v1'"),
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


class FrCanonicalField(Base, TimestampMixin, FieldRegistryMixin):
    __tablename__ = "fr_canonical_fields"
    __table_args__ = (
        UniqueConstraint("tenant_id", "qualified_code", name="uq_fr_canonical_fields_scope_code"),
    )

    qualified_code: Mapped[str] = mapped_column(String(191), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    field_type: Mapped[str] = mapped_column(String(32), nullable=False)
    label_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ownership: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_domain: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pii_class: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


class FrCardLayoutProfile(Base, TimestampMixin, FieldRegistryMixin):
    __tablename__ = "fr_card_layout_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", "code", name="uq_fr_card_layout_profiles_scope_code"),
    )

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )


class FrCardLayoutField(Base, TimestampMixin):
    __tablename__ = "fr_card_layout_fields"
    __table_args__ = (
        UniqueConstraint(
            "layout_profile_id",
            "canonical_field_id",
            name="uq_fr_card_layout_fields_layout_field",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    layout_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fr_card_layout_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canonical_field_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fr_canonical_fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_code: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    label_override: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


__all__ = [
    "DEFAULT_REGISTRY_VERSION",
    "PLATFORM_TENANT_SCOPE",
    "REGISTRY_STATUS_ACTIVE",
    "REGISTRY_STATUS_ARCHIVED",
    "REGISTRY_STATUS_DRAFT",
    "FrCanonicalField",
    "FrCardLayoutField",
    "FrCardLayoutProfile",
]
