"""Universal Funnel model for flexible pipeline stages (candidates, leads, deals)."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.candidate import Candidate
    from backend.app.models.lead import Lead
    from backend.app.models.vacancy import Vacancy


class Funnel(Base):
    """Funnel definition (e.g. Driver Recruitment, Lead Sales)."""

    __tablename__ = "funnels"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    module_key: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="ADR-004 product module owner (e.g. recruitment)",
    )
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # candidate | lead | deal
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    __table_args__ = (
        Index("ix_funnels_tenant_company_module", "tenant_id", "company_id", "module_key"),
        Index("ix_funnels_tenant_module_type", "tenant_id", "module_key", "type"),
    )

    stages: Mapped[list["FunnelStage"]] = relationship(
        "FunnelStage",
        back_populates="funnel",
        order_by="FunnelStage.order",
        cascade="all, delete-orphan",
    )


class FunnelStage(Base):
    """Stage within a funnel."""

    __tablename__ = "funnel_stages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    funnel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("funnels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    # Canonical system skeleton bucket used for analytics and workflow invariants.
    system_stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default="in_progress", server_default="in_progress"
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_terminal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # §2.3 pipeline: owner_role, required_actions, sla_hours, auto_rules (JSON blob v1).
    stage_contract_v1: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # §2.12: maps this pipeline stage to a cross-tenant "root" funnel bucket (lead funnels only).
    conversion_root_v1: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    pe_maps_to_module: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="Process Engine system stage module (P1)"
    )
    pe_maps_to_code: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="Process Engine system stage code (P1)"
    )

    __table_args__ = (
        UniqueConstraint("funnel_id", "code", name="uq_funnel_stage_code"),
    )

    funnel: Mapped["Funnel"] = relationship("Funnel", back_populates="stages")
