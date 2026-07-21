"""C2.2 PR-1 — Automation Engine domain entities (durable SoT).

Intent-only: Event → Rules → Decision records. No send path / Thread mutation.
ORM names use CommunicationAutomation* to avoid colliding with legacy
``models.automation_rule.AutomationRule`` (tenant reminder rules).
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

RULE_STATUS_ACTIVE = "active"
RULE_STATUS_ARCHIVED = "archived"

VERSION_STATUS_DRAFT = "draft"
VERSION_STATUS_PUBLISHED = "published"

DECISION_OUTCOME_FIRE = "fire"
DECISION_OUTCOME_SKIP = "skip"

RECIPIENT_STRATEGIES = frozenset(
    {
        "origin_primary",
        "context_path",
        "explicit",
    }
)


class CommunicationAutomationRule(Base, TimestampMixin):
    """Stable automation rule identity within a tenant."""

    __tablename__ = "communication_automation_rules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_comm_auto_rules_tenant_key"),
        Index("ix_comm_auto_rules_tenant_status", "tenant_id", "status"),
        Index("ix_comm_auto_rules_tenant_enabled", "tenant_id", "enabled"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=RULE_STATUS_ACTIVE
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    versions: Mapped[list["CommunicationAutomationRuleVersion"]] = relationship(
        "CommunicationAutomationRuleVersion",
        back_populates="rule",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CommunicationAutomationRuleVersion(Base, TimestampMixin):
    """Draft (editable) or published (immutable) rule body."""

    __tablename__ = "communication_automation_rule_versions"
    __table_args__ = (
        Index("ix_comm_auto_ver_tenant_rule", "tenant_id", "rule_id"),
        Index("ix_comm_auto_ver_tenant_status", "tenant_id", "status"),
        UniqueConstraint(
            "tenant_id",
            "rule_id",
            "version_number",
            name="uq_comm_auto_ver_tenant_rule_number",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_automation_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Draft uses version_number=0; published versions are 1..N.
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=VERSION_STATUS_DRAFT
    )
    # Declarative match tree (evaluated in PR-2; stored as JSON in PR-1).
    conditions: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    intent_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    preferred_template_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    channel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    recipient_strategy: Mapped[str] = mapped_column(
        String(64), nullable=False, default="origin_primary"
    )
    recipient_config: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    variables_mapping: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    rule: Mapped[CommunicationAutomationRule] = relationship(
        "CommunicationAutomationRule", back_populates="versions"
    )
    triggers: Mapped[list["CommunicationAutomationTrigger"]] = relationship(
        "CommunicationAutomationTrigger",
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


class CommunicationAutomationTrigger(Base, TimestampMixin):
    """Event binding for a rule version (event_type + optional filter)."""

    __tablename__ = "communication_automation_triggers"
    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "event_type",
            name="uq_comm_auto_trigger_version_event",
        ),
        Index("ix_comm_auto_trigger_version", "version_id"),
        Index("ix_comm_auto_trigger_event_type", "event_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_automation_rule_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    event_filter: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)

    version: Mapped[CommunicationAutomationRuleVersion] = relationship(
        "CommunicationAutomationRuleVersion", back_populates="triggers"
    )


class CommunicationAutomationDecision(Base, TimestampMixin):
    """Durable evaluate outcome (fire | skip) for diagnostics / replay."""

    __tablename__ = "communication_automation_decisions"
    __table_args__ = (
        Index("ix_comm_auto_dec_tenant_created", "tenant_id", "created_at"),
        Index("ix_comm_auto_dec_tenant_rule", "tenant_id", "rule_id"),
        Index("ix_comm_auto_dec_tenant_event", "tenant_id", "source_event_id"),
        Index("ix_comm_auto_dec_tenant_outcome", "tenant_id", "outcome"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_version_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trigger_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    source_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_codes: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    intent_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # IntentExecutionRequest-shaped inputs only — never a send result.
    intent_request_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONType, nullable=True
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)


# Spec names (C2.2) → ORM classes (package-local aliases; not global models.AutomationRule)
AutomationRule = CommunicationAutomationRule
AutomationRuleVersion = CommunicationAutomationRuleVersion
AutomationTrigger = CommunicationAutomationTrigger
AutomationDecision = CommunicationAutomationDecision

__all__ = [
    "CommunicationAutomationRule",
    "CommunicationAutomationRuleVersion",
    "CommunicationAutomationTrigger",
    "CommunicationAutomationDecision",
    "AutomationRule",
    "AutomationRuleVersion",
    "AutomationTrigger",
    "AutomationDecision",
    "RULE_STATUS_ACTIVE",
    "RULE_STATUS_ARCHIVED",
    "VERSION_STATUS_DRAFT",
    "VERSION_STATUS_PUBLISHED",
    "DECISION_OUTCOME_FIRE",
    "DECISION_OUTCOME_SKIP",
    "RECIPIENT_STRATEGIES",
]
