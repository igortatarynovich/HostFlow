"""C2.1 PR-1 — Template Platform domain entities (durable SoT).

Presentation only: how a message looks. No routing / consent / Thread logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

TEMPLATE_STATUS_ACTIVE = "active"
TEMPLATE_STATUS_ARCHIVED = "archived"

VERSION_STATUS_DRAFT = "draft"
VERSION_STATUS_PUBLISHED = "published"

VARIABLE_TYPES = frozenset({"string", "text", "url", "email", "number", "bool", "datetime"})


class CommunicationTemplate(Base, TimestampMixin):
    """Stable template identity within a tenant."""

    __tablename__ = "communication_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_comm_templates_tenant_key"),
        Index("ix_comm_templates_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=TEMPLATE_STATUS_ACTIVE
    )

    versions: Mapped[list["CommunicationTemplateVersion"]] = relationship(
        "CommunicationTemplateVersion",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CommunicationTemplateVersion(Base, TimestampMixin):
    """Draft (editable) or published (immutable) template body."""

    __tablename__ = "communication_template_versions"
    __table_args__ = (
        Index("ix_comm_tpl_ver_tenant_template", "tenant_id", "template_id"),
        Index("ix_comm_tpl_ver_tenant_status", "tenant_id", "status"),
        UniqueConstraint(
            "tenant_id",
            "template_id",
            "version_number",
            name="uq_comm_tpl_ver_tenant_template_number",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Draft uses version_number=0; published versions are 1..N.
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=VERSION_STATUS_DRAFT
    )
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="pl")
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    template: Mapped[CommunicationTemplate] = relationship(
        "CommunicationTemplate", back_populates="versions"
    )
    variables: Mapped[list["CommunicationTemplateVariable"]] = relationship(
        "CommunicationTemplateVariable",
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    channel_bindings: Mapped[list["CommunicationTemplateChannelBinding"]] = relationship(
        "CommunicationTemplateChannelBinding",
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    intent_bindings: Mapped[list["CommunicationTemplateIntentBinding"]] = relationship(
        "CommunicationTemplateIntentBinding",
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def is_draft(self) -> bool:
        return str(self.status) == VERSION_STATUS_DRAFT

    @property
    def is_published(self) -> bool:
        return str(self.status) == VERSION_STATUS_PUBLISHED


class CommunicationTemplateVariable(Base, TimestampMixin):
    __tablename__ = "communication_template_variables"
    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "name",
            name="uq_comm_tpl_var_version_name",
        ),
        Index("ix_comm_tpl_var_version", "version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_template_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    var_type: Mapped[str] = mapped_column(String(32), nullable=False, default="string")
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    version: Mapped[CommunicationTemplateVersion] = relationship(
        "CommunicationTemplateVersion", back_populates="variables"
    )


class CommunicationTemplateChannelBinding(Base, TimestampMixin):
    __tablename__ = "communication_template_channel_bindings"
    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "channel",
            name="uq_comm_tpl_channel_version_channel",
        ),
        Index("ix_comm_tpl_channel_version", "version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_template_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)

    version: Mapped[CommunicationTemplateVersion] = relationship(
        "CommunicationTemplateVersion", back_populates="channel_bindings"
    )


class CommunicationTemplateIntentBinding(Base, TimestampMixin):
    __tablename__ = "communication_template_intent_bindings"
    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "intent_key",
            name="uq_comm_tpl_intent_version_intent",
        ),
        Index("ix_comm_tpl_intent_version", "version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_template_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    intent_key: Mapped[str] = mapped_column(String(128), nullable=False)

    version: Mapped[CommunicationTemplateVersion] = relationship(
        "CommunicationTemplateVersion", back_populates="intent_bindings"
    )


# Spec names (C2.1) → ORM classes
Template = CommunicationTemplate
TemplateVersion = CommunicationTemplateVersion
TemplateVariable = CommunicationTemplateVariable
TemplateChannelBinding = CommunicationTemplateChannelBinding
TemplateIntentBinding = CommunicationTemplateIntentBinding

__all__ = [
    "CommunicationTemplate",
    "CommunicationTemplateVersion",
    "CommunicationTemplateVariable",
    "CommunicationTemplateChannelBinding",
    "CommunicationTemplateIntentBinding",
    "Template",
    "TemplateVersion",
    "TemplateVariable",
    "TemplateChannelBinding",
    "TemplateIntentBinding",
    "TEMPLATE_STATUS_ACTIVE",
    "TEMPLATE_STATUS_ARCHIVED",
    "VERSION_STATUS_DRAFT",
    "VERSION_STATUS_PUBLISHED",
    "VARIABLE_TYPES",
]
