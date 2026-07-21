"""C2.3 PR-1 — Campaign Orchestrator domain entities (durable SoT).

Intent-only orchestration: audience definition + run snapshot + run items.
No send path / Thread / Message / Delivery writes in this package.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
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

# Campaign head lifecycle
CAMPAIGN_STATUS_DRAFT = "draft"
CAMPAIGN_STATUS_ACTIVE = "active"
CAMPAIGN_STATUS_PAUSED = "paused"
CAMPAIGN_STATUS_ARCHIVED = "archived"
CampaignStatus = frozenset(
    {
        CAMPAIGN_STATUS_DRAFT,
        CAMPAIGN_STATUS_ACTIVE,
        CAMPAIGN_STATUS_PAUSED,
        CAMPAIGN_STATUS_ARCHIVED,
    }
)

# Version lifecycle (mirror Template / Automation)
VERSION_STATUS_DRAFT = "draft"
VERSION_STATUS_PUBLISHED = "published"

# Run lifecycle
CAMPAIGN_RUN_STATUS_PENDING = "pending"
CAMPAIGN_RUN_STATUS_RUNNING = "running"
CAMPAIGN_RUN_STATUS_COMPLETED = "completed"
CAMPAIGN_RUN_STATUS_FAILED = "failed"
CAMPAIGN_RUN_STATUS_CANCELLED = "cancelled"
CampaignRunStatus = frozenset(
    {
        CAMPAIGN_RUN_STATUS_PENDING,
        CAMPAIGN_RUN_STATUS_RUNNING,
        CAMPAIGN_RUN_STATUS_COMPLETED,
        CAMPAIGN_RUN_STATUS_FAILED,
        CAMPAIGN_RUN_STATUS_CANCELLED,
    }
)

# Per-recipient item lifecycle
RUN_ITEM_STATUS_PENDING = "pending"
RUN_ITEM_STATUS_READY = "ready"
RUN_ITEM_STATUS_EMITTED = "emitted"
RUN_ITEM_STATUS_SKIPPED = "skipped"
RUN_ITEM_STATUS_FAILED = "failed"
CampaignRunItemStatus = frozenset(
    {
        RUN_ITEM_STATUS_PENDING,
        RUN_ITEM_STATUS_READY,
        RUN_ITEM_STATUS_EMITTED,
        RUN_ITEM_STATUS_SKIPPED,
        RUN_ITEM_STATUS_FAILED,
    }
)


class CommunicationCampaign(Base, TimestampMixin):
    """Stable campaign identity within a tenant."""

    __tablename__ = "communication_campaigns"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_comm_campaigns_tenant_key"),
        Index("ix_comm_campaigns_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CAMPAIGN_STATUS_ACTIVE
    )

    versions: Mapped[list["CommunicationCampaignVersion"]] = relationship(
        "CommunicationCampaignVersion",
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    runs: Mapped[list["CommunicationCampaignRun"]] = relationship(
        "CommunicationCampaignRun",
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CommunicationCampaignVersion(Base, TimestampMixin):
    """Draft (editable) or published (immutable) campaign plan + audience definition."""

    __tablename__ = "communication_campaign_versions"
    __table_args__ = (
        Index("ix_comm_camp_ver_tenant_campaign", "tenant_id", "campaign_id"),
        Index("ix_comm_camp_ver_tenant_status", "tenant_id", "status"),
        UniqueConstraint(
            "tenant_id",
            "campaign_id",
            "version_number",
            name="uq_comm_camp_ver_tenant_campaign_number",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Draft uses version_number=0; published versions are 1..N.
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=VERSION_STATUS_DRAFT
    )
    intent_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    preferred_template_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    channel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    # Wave / plan knobs for later orchestration PRs (opaque in PR-1).
    plan: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    campaign: Mapped[CommunicationCampaign] = relationship(
        "CommunicationCampaign", back_populates="versions"
    )
    audience_definition: Mapped[Optional["CommunicationCampaignAudienceDefinition"]] = (
        relationship(
            "CommunicationCampaignAudienceDefinition",
            back_populates="version",
            cascade="all, delete-orphan",
            uselist=False,
            lazy="selectin",
        )
    )

    @property
    def is_draft(self) -> bool:
        return str(self.status) == VERSION_STATUS_DRAFT

    @property
    def is_published(self) -> bool:
        return str(self.status) == VERSION_STATUS_PUBLISHED


class CommunicationCampaignAudienceDefinition(Base, TimestampMixin):
    """Audience *definition* (selection rule) bound to a CampaignVersion.

    Not a recipient list. Snapshot lives on CampaignRun → CampaignRecipient.
    """

    __tablename__ = "communication_campaign_audience_definitions"
    __table_args__ = (
        UniqueConstraint("version_id", name="uq_comm_camp_audience_def_version"),
        Index("ix_comm_camp_audience_def_version", "version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_campaign_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    # e.g. filter_tree | entity_list | query_key — opaque to PR-1 lifecycle.
    definition_type: Mapped[str] = mapped_column(String(64), nullable=False, default="filter")
    # Declarative selection rule (resolved in PR-2).
    definition: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)

    version: Mapped[CommunicationCampaignVersion] = relationship(
        "CommunicationCampaignVersion", back_populates="audience_definition"
    )


class CommunicationCampaignRun(Base, TimestampMixin):
    """One execution against a concrete published (or pinned) campaign_version_id."""

    __tablename__ = "communication_campaign_runs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_comm_camp_runs_tenant_idempotency",
        ),
        Index("ix_comm_camp_runs_tenant_campaign", "tenant_id", "campaign_id"),
        Index("ix_comm_camp_runs_tenant_version", "tenant_id", "campaign_version_id"),
        Index("ix_comm_camp_runs_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Required: run always pins a specific version (reproducibility).
    campaign_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_campaign_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CAMPAIGN_RUN_STATUS_PENDING
    )
    # Snapshot metadata (counts, frozen_at, definition fingerprint) — not the live rule.
    audience_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)

    campaign: Mapped[CommunicationCampaign] = relationship(
        "CommunicationCampaign", back_populates="runs"
    )
    version: Mapped[CommunicationCampaignVersion] = relationship(
        "CommunicationCampaignVersion"
    )
    recipients: Mapped[list["CommunicationCampaignRecipient"]] = relationship(
        "CommunicationCampaignRecipient",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    items: Mapped[list["CommunicationCampaignRunItem"]] = relationship(
        "CommunicationCampaignRunItem",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CommunicationCampaignRecipient(Base, TimestampMixin):
    """Audience *snapshot* member for a specific Run (immutable after create)."""

    __tablename__ = "communication_campaign_recipients"
    __table_args__ = (
        Index("ix_comm_camp_recip_run", "run_id"),
        UniqueConstraint(
            "run_id",
            "entity_type",
            "entity_id",
            "address",
            name="uq_comm_camp_recip_run_entity_address",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_campaign_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(320), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Frozen context for this recipient at snapshot time.
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)

    run: Mapped[CommunicationCampaignRun] = relationship(
        "CommunicationCampaignRun", back_populates="recipients"
    )
    item: Mapped[Optional["CommunicationCampaignRunItem"]] = relationship(
        "CommunicationCampaignRunItem",
        back_populates="recipient",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CommunicationCampaignRunItem(Base, TimestampMixin):
    """Per-recipient processing state within a Run (isolated failures)."""

    __tablename__ = "communication_campaign_run_items"
    __table_args__ = (
        UniqueConstraint("run_id", "recipient_id", name="uq_comm_camp_item_run_recipient"),
        Index("ix_comm_camp_item_run_status", "run_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_campaign_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("communication_campaign_recipients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=RUN_ITEM_STATUS_PENDING
    )
    reason_codes: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    reason_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Filled by later Intent-emission PR — never a provider/message id in PR-1.
    intent_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_event_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)

    run: Mapped[CommunicationCampaignRun] = relationship(
        "CommunicationCampaignRun", back_populates="items"
    )
    recipient: Mapped[CommunicationCampaignRecipient] = relationship(
        "CommunicationCampaignRecipient", back_populates="item"
    )


# Spec names (C2.3) → ORM classes
Campaign = CommunicationCampaign
CampaignVersion = CommunicationCampaignVersion
CampaignAudienceDefinition = CommunicationCampaignAudienceDefinition
CampaignRecipient = CommunicationCampaignRecipient
CampaignRun = CommunicationCampaignRun
CampaignRunItem = CommunicationCampaignRunItem

__all__ = [
    "CommunicationCampaign",
    "CommunicationCampaignVersion",
    "CommunicationCampaignAudienceDefinition",
    "CommunicationCampaignRecipient",
    "CommunicationCampaignRun",
    "CommunicationCampaignRunItem",
    "Campaign",
    "CampaignVersion",
    "CampaignAudienceDefinition",
    "CampaignRecipient",
    "CampaignRun",
    "CampaignRunItem",
    "CampaignStatus",
    "CampaignRunStatus",
    "CampaignRunItemStatus",
    "CAMPAIGN_STATUS_DRAFT",
    "CAMPAIGN_STATUS_ACTIVE",
    "CAMPAIGN_STATUS_PAUSED",
    "CAMPAIGN_STATUS_ARCHIVED",
    "VERSION_STATUS_DRAFT",
    "VERSION_STATUS_PUBLISHED",
    "CAMPAIGN_RUN_STATUS_PENDING",
    "CAMPAIGN_RUN_STATUS_RUNNING",
    "CAMPAIGN_RUN_STATUS_COMPLETED",
    "CAMPAIGN_RUN_STATUS_FAILED",
    "CAMPAIGN_RUN_STATUS_CANCELLED",
    "RUN_ITEM_STATUS_PENDING",
    "RUN_ITEM_STATUS_READY",
    "RUN_ITEM_STATUS_EMITTED",
    "RUN_ITEM_STATUS_SKIPPED",
    "RUN_ITEM_STATUS_FAILED",
]
