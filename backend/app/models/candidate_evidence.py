"""Candidate Evidence — links a requirement to a chosen evidence variant and document instances."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .enums import CandidateEvidenceStatus

if TYPE_CHECKING:
    from .document import Document


class CandidateEvidence(Base):
    """A candidate's chosen way to satisfy a recruitment requirement."""

    __tablename__ = "candidate_evidence"
    __table_args__ = (
        Index("ix_candidate_evidence_tenant_candidate", "tenant_id", "candidate_id"),
        Index(
            "ix_candidate_evidence_tenant_candidate_requirement",
            "tenant_id",
            "candidate_id",
            "requirement_code",
        ),
        Index("ix_candidate_evidence_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    requirement_code: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_variant_code: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CandidateEvidenceStatus.draft.value
    )
    selected_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    selected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    superseded_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    superseded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_evidence_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("candidate_evidence.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    documents: Mapped[list["CandidateEvidenceDocument"]] = relationship(
        "CandidateEvidenceDocument",
        back_populates="candidate_evidence",
        cascade="all, delete-orphan",
    )


class CandidateEvidenceDocument(Base):
    """Junction: document instance linked to a candidate evidence row."""

    __tablename__ = "candidate_evidence_documents"
    __table_args__ = (
        UniqueConstraint(
            "candidate_evidence_id",
            "document_id",
            name="uq_candidate_evidence_documents_evidence_document",
        ),
        Index("ix_candidate_evidence_documents_tenant", "tenant_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    candidate_evidence_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_evidence.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    linked_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    candidate_evidence: Mapped["CandidateEvidence"] = relationship(
        "CandidateEvidence", back_populates="documents"
    )
    document: Mapped["Document"] = relationship("Document")
