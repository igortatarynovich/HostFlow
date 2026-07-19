"""Forms P2.4 — Builder draft tip + append-only revision ledger.

Draft storage is NOT a Catalog or publication Source of Truth.
Composition payloads are frozen per revision; tip uses optimistic revision pin.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base
from .mixins import now_utc

JSONAnyType = SQLiteJSON().with_variant(JSONB, "postgresql")

STATUS_ACTIVE = "active"
STATUS_ARCHIVED = "archived"


class FormBuilderDraft(Base):
    """Current tip of a tenant-scoped Builder draft."""

    __tablename__ = "form_builder_drafts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "draft_id", name="uq_form_builder_drafts_tenant_draft"),
        Index("ix_form_builder_drafts_tenant_status", "tenant_id", "status"),
        Index("ix_form_builder_drafts_tenant_updated", "tenant_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    draft_id: Mapped[str] = mapped_column(String(64), nullable=False)
    form_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=STATUS_ACTIVE)
    composition_contract: Mapped[str] = mapped_column(
        String(64), nullable=False, default="forms.builder.composition.v1"
    )
    # Frozen tip payload (forms.builder.composition.v1 dict) — replaced only with revision bump.
    composition: Mapped[dict] = mapped_column(JSONAnyType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class FormBuilderDraftRevision(Base):
    """Append-only immutable composition payload for one draft revision."""

    __tablename__ = "form_builder_draft_revisions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "draft_id",
            "revision",
            name="uq_form_builder_draft_revs_tenant_draft_rev",
        ),
        Index("ix_form_builder_draft_revs_tenant_draft", "tenant_id", "draft_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    draft_id: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    composition_contract: Mapped[str] = mapped_column(String(64), nullable=False)
    composition: Mapped[dict] = mapped_column(JSONAnyType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


__all__ = [
    "STATUS_ACTIVE",
    "STATUS_ARCHIVED",
    "FormBuilderDraft",
    "FormBuilderDraftRevision",
]
