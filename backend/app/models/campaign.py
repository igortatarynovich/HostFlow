"""ADR-024 Stage 3A/3B/3D — Campaign foundation, Endpoint bindings, Result/Outcome."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from ..db.base import Base
from .mixins import TimestampMixin


class Campaign(Base, TimestampMixin):
    """Long-lived acquisition initiative (not a Meta campaign, not a single wave).

    CampaignGoal (ADR-024): in Stage 3A / V1 the goal is stored inline as
    ``goal_type`` + ``primary_kpi`` on this row (ADR allows Campaign or
    CampaignGoal entity). No separate ``acq_campaign_goals`` table yet.
    """

    __tablename__ = "acq_campaigns"
    __table_args__ = (
        Index("ix_acq_campaigns_tenant_company", "tenant_id", "own_company_id"),
        Index("ix_acq_campaigns_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    own_company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    # CampaignGoal fields — registry-validated pair (Goal Type + Primary KPI).
    goal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_kpi: Mapped[str] = mapped_column(String(64), nullable=False)
    current_flight_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    targets: Mapped[list["CampaignTarget"]] = relationship(
        "CampaignTarget",
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    flights: Mapped[list["CampaignRun"]] = relationship(
        "CampaignRun",
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CampaignRun.created_at",
    )


class CampaignRun(Base, TimestampMixin):
    """Flight / wave inside a Campaign. Stage 3A always creates exactly one."""

    __tablename__ = "acq_campaign_runs"
    __table_args__ = (
        UniqueConstraint("campaign_id", "code", name="uq_acq_campaign_runs_campaign_code"),
        Index("ix_acq_campaign_runs_tenant_campaign", "tenant_id", "campaign_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, default="flight_1")
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Flight 1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="flights")
    form_links: Mapped[list["CampaignRunForm"]] = relationship(
        "CampaignRunForm",
        back_populates="campaign_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    intake_source_links: Mapped[list["CampaignRunIntakeSource"]] = relationship(
        "CampaignRunIntakeSource",
        back_populates="campaign_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CampaignTarget(Base, TimestampMixin):
    """Universal promotion target — no typed FK to vacancy/service/client (ADR-024)."""

    __tablename__ = "acq_campaign_targets"
    __table_args__ = (
        Index("ix_acq_campaign_targets_tenant_campaign", "tenant_id", "campaign_id"),
        Index("ix_acq_campaign_targets_type_id", "target_type", "target_id"),
        UniqueConstraint(
            "campaign_id",
            "target_type",
            "target_id",
            "role",
            name="uq_acq_campaign_targets_campaign_type_id_role",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # Always set from registry — never trusted from the client.
    target_module: Mapped[str] = mapped_column(String(32), nullable=False)
    route_intent: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="primary")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="targets")


class CampaignRunForm(Base, TimestampMixin):
    """Association: Flight uses Form (Forms remain SoT — ADR-024 Stage 3B)."""

    __tablename__ = "acq_campaign_run_forms"
    __table_args__ = (
        UniqueConstraint("campaign_run_id", "form_id", name="uq_acq_campaign_run_forms_run_form"),
        Index("ix_acq_campaign_run_forms_tenant_run", "tenant_id", "campaign_run_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    campaign_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaign_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    form_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenant_lead_forms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="primary")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    campaign_run: Mapped["CampaignRun"] = relationship("CampaignRun", back_populates="form_links")


class CampaignRunIntakeSource(Base, TimestampMixin):
    """Association: Flight uses IntakeSourceProfile (Intake remains SoT — ADR-024 Stage 3B).

    No provider/external_ref snapshots — resolve from IntakeSourceProfile /
    IntakeSourceBinding at read time (single SoT).
    """

    __tablename__ = "acq_campaign_run_intake_sources"
    __table_args__ = (
        UniqueConstraint(
            "campaign_run_id",
            "intake_source_profile_id",
            name="uq_acq_campaign_run_intake_sources_run_profile",
        ),
        Index("ix_acq_campaign_run_intake_sources_tenant_run", "tenant_id", "campaign_run_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    campaign_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaign_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intake_source_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("intake_source_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="primary")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    campaign_run: Mapped["CampaignRun"] = relationship(
        "CampaignRun", back_populates="intake_source_links"
    )


class CampaignResultAttribution(Base, TimestampMixin):
    """Stage 3D — automatic Result → Campaign/Flight/Endpoint/Submission attribution.

    Ownership: Attribution is an Acquisition projection. Domain Results remain owned by
    destination modules — ``result_type`` + ``result_id`` are opaque refs (no typed FK
    to Candidate / Application / Inquiry / Client).
    """

    __tablename__ = "acq_result_attributions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "result_type",
            "result_id",
            name="uq_acq_result_attributions_tenant_result",
        ),
        UniqueConstraint(
            "tenant_id",
            "submission_id",
            name="uq_acq_result_attributions_tenant_submission",
        ),
        Index("ix_acq_result_attributions_tenant_campaign", "tenant_id", "campaign_id"),
        Index("ix_acq_result_attributions_tenant_flight", "tenant_id", "campaign_run_id"),
        Index("ix_acq_result_attributions_tenant_lead", "tenant_id", "lead_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaign_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Opaque Operations Result identity (no FK into domain tables).
    result_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result_id: Mapped[str] = mapped_column(String(64), nullable=False)
    submission_id: Mapped[str] = mapped_column(String(36), nullable=False)
    lead_id: Mapped[str] = mapped_column(String(36), nullable=False)
    route_intent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # V1 transitional Endpoint identity (Form / Intake Source specializations).
    endpoint_form_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    endpoint_intake_source_profile_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    routing_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class CampaignOutcome(Base, TimestampMixin):
    """Stage 3D PR-2 — Acquisition Outcome (progress toward Campaign goal).

    Outcome is **not** a Result status. Results feed Outcome via ledger links;
    progress is monotonic (soft-revoke does not decrease ``progress_current``).
    """

    __tablename__ = "acq_outcomes"
    __table_args__ = (
        Index("ix_acq_outcomes_tenant_campaign", "tenant_id", "campaign_id"),
        Index("ix_acq_outcomes_tenant_flight", "tenant_id", "campaign_run_id"),
        Index("ix_acq_outcomes_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Flight id (CampaignRun). Named campaign_run_id in DB; exposed as flight_id in services.
    campaign_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaign_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    progress_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_target: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    result_links: Mapped[list["CampaignOutcomeResultLink"]] = relationship(
        "CampaignOutcomeResultLink",
        back_populates="outcome",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CampaignOutcomeResultLink(Base, TimestampMixin):
    """Ledger: Outcome ← attributed Result.

    Soft-revoke (``revoked_at``) keeps audit history and does **not** decrease
    Outcome.progress_current — Outcome reflects attained business progress.
    """

    __tablename__ = "acq_outcome_result_links"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "outcome_id",
            "result_type",
            "result_id",
            name="uq_acq_outcome_result_links_outcome_result",
        ),
        UniqueConstraint(
            "tenant_id",
            "attribution_id",
            name="uq_acq_outcome_result_links_attribution",
        ),
        Index("ix_acq_outcome_result_links_tenant_outcome", "tenant_id", "outcome_id"),
        Index(
            "ix_acq_outcome_result_links_tenant_result",
            "tenant_id",
            "result_type",
            "result_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    outcome_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_outcomes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attribution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_result_attributions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result_id: Mapped[str] = mapped_column(String(64), nullable=False)
    counted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    outcome: Mapped["CampaignOutcome"] = relationship(
        "CampaignOutcome", back_populates="result_links"
    )


class CampaignFlightSpendEntry(Base, TimestampMixin):
    """Canonical Flight spend source (Stage 3D PR-3).

    Not a KPI row — aggregates read and sum these entries. Amounts are Decimal/NUMERIC;
    currency is ISO-4217; mixed currencies must not be summed by the KPI service.
    """

    __tablename__ = "acq_flight_spend_entries"
    __table_args__ = (
        Index("ix_acq_flight_spend_entries_tenant_flight", "tenant_id", "campaign_run_id"),
        Index("ix_acq_flight_spend_entries_tenant_campaign", "tenant_id", "campaign_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_campaign_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class CampaignResultQualification(Base, TimestampMixin):
    """Explicit qualification contract (Stage 3D PR-3).

    An attributed Result counts as Qualified **only** when this row exists.
    """

    __tablename__ = "acq_result_qualifications"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "attribution_id",
            name="uq_acq_result_qualifications_attribution",
        ),
        Index("ix_acq_result_qualifications_tenant_attr", "tenant_id", "attribution_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    attribution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("acq_result_attributions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qualified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
