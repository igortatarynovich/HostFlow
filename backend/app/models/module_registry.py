"""Module Registry / Marketplace Installation platform models (P1)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

MODULE_REGISTRY_VERSION = "module_registry_v1"

MODULE_KIND_BUSINESS = "business_module"
MODULE_KIND_PLATFORM = "platform_capability"

MODULE_STATUS_REGISTERED = "registered"
MODULE_STATUS_DEPRECATED = "deprecated"
MODULE_STATUS_HIDDEN = "hidden"

INSTALLATION_STATE_INSTALLED = "installed"
INSTALLATION_STATE_ENABLED = "enabled"
INSTALLATION_STATE_SUSPENDED = "suspended"
INSTALLATION_STATE_UNINSTALLED = "uninstalled"

INSTALLATION_SOURCE_SYSTEM = "system"
INSTALLATION_SOURCE_MIGRATION = "migration"


class ModuleRegistry(Base, TimestampMixin):
    __tablename__ = "module_registry"
    __table_args__ = (
        UniqueConstraint("module_code", name="uq_module_registry_module_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    module_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    owner: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=MODULE_STATUS_REGISTERED,
        server_default=text("'registered'"),
        index=True,
    )
    registry_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=MODULE_REGISTRY_VERSION,
        server_default=text("'module_registry_v1'"),
    )
    manifest: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )


class TenantModuleInstallation(Base, TimestampMixin):
    __tablename__ = "tenant_module_installations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module_code", name="uq_tenant_module_installations_scope"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    module_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=INSTALLATION_STATE_ENABLED,
        server_default=text("'enabled'"),
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=INSTALLATION_SOURCE_MIGRATION,
        server_default=text("'migration'"),
    )
    settings_json: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )


class ModuleCapability(Base, TimestampMixin):
    __tablename__ = "module_capabilities"
    __table_args__ = (
        UniqueConstraint("module_code", "capability_code", name="uq_module_capabilities_module_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    module_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    capability_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )


class ModuleDependency(Base, TimestampMixin):
    __tablename__ = "module_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "module_code",
            "dependency_module_code",
            "dependency_kind",
            name="uq_module_dependencies_module_dependency_kind",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    module_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dependency_module_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dependency_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="optional")
    capability_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )


__all__ = [
    "INSTALLATION_SOURCE_MIGRATION",
    "INSTALLATION_SOURCE_SYSTEM",
    "INSTALLATION_STATE_ENABLED",
    "INSTALLATION_STATE_INSTALLED",
    "INSTALLATION_STATE_SUSPENDED",
    "INSTALLATION_STATE_UNINSTALLED",
    "MODULE_KIND_BUSINESS",
    "MODULE_KIND_PLATFORM",
    "MODULE_REGISTRY_VERSION",
    "MODULE_STATUS_DEPRECATED",
    "MODULE_STATUS_HIDDEN",
    "MODULE_STATUS_REGISTERED",
    "ModuleCapability",
    "ModuleDependency",
    "ModuleRegistry",
    "TenantModuleInstallation",
]
