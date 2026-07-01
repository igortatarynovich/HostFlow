"""Entity Profile Definition Registry models (P1).

Composition layer between Field Registry and Intake / Process runtime.
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
JSONAnyType = SQLiteJSON().with_variant(JSONB, "postgresql")

PLATFORM_TENANT_SCOPE = ""


class EntityProfileMixin:
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        default=PLATFORM_TENANT_SCOPE,
        server_default=text("''"),
        index=True,
        comment="Empty string = platform catalog; otherwise tenant-scoped row",
    )
    profile_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    registry_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="entity_profile_v1",
        server_default=text("'entity_profile_v1'"),
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )


class EpEntityProfile(Base, TimestampMixin, EntityProfileMixin):
    __tablename__ = "ep_entity_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "profile_code", name="uq_ep_entity_profiles_scope_code"),
    )

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    module_owner: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    default_layout_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    document_pack_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    process_profile_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )


class EpEntityProfileField(Base, TimestampMixin):
    __tablename__ = "ep_entity_profile_fields"
    __table_args__ = (
        UniqueConstraint(
            "entity_profile_id",
            "qualified_code",
            name="uq_ep_entity_profile_fields_profile_code",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    entity_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ep_entity_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qualified_code: Mapped[str] = mapped_column(String(191), nullable=False, index=True)
    canonical_field_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("fr_canonical_fields.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    intake_level: Mapped[str] = mapped_column(
        String(16), nullable=False, default="optional", server_default=text("'optional'")
    )
    card_save_level: Mapped[str] = mapped_column(
        String(16), nullable=False, default="optional", server_default=text("'optional'")
    )
    transition_level: Mapped[str] = mapped_column(
        String(16), nullable=False, default="optional", server_default=text("'optional'")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )


class EpIntakePresentation(Base, TimestampMixin):
    __tablename__ = "ep_intake_presentations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "presentation_code",
            name="uq_ep_intake_presentations_scope_code",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        default=PLATFORM_TENANT_SCOPE,
        server_default=text("''"),
        index=True,
    )
    entity_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ep_entity_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intake_source_binding_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    presentation_code: Mapped[str] = mapped_column(String(128), nullable=False)
    field_subset: Mapped[list[Any]] = mapped_column(
        JSONAnyType,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    presentation_overrides: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )


__all__ = [
    "PLATFORM_TENANT_SCOPE",
    "EpEntityProfile",
    "EpEntityProfileField",
    "EpIntakePresentation",
]
