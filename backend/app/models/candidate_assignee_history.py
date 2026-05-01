"""Append-only audit trail for ``Candidate.recruiter_id`` reassignments.

Phase 2.6.G-5 Stage C — canonical history table that backs every single write
to :attr:`Candidate.recruiter_id`. See ``docs/specs/manager-assignment.md``
§2.5 for the full spec and §4 Stage C for the roll-out plan.

Consumers:

- Explainability popover on candidate card ("откуда этот assignee", G-10).
- Support workflow ("почему кандидата забрали у Ани").
- Routing-quality / load-balancing analytics (future).

Table invariants:

- Append-only — rows are never UPDATEd or DELETEd by application code.
- ``changed_at`` is stored in timezone-aware UTC to match other audit tables
  (``activity_log``, ``candidate_stage_history``).
- ``from_user_id`` and ``to_user_id`` are nullable: a brand-new candidate may
  have ``from_user_id = NULL`` (first assignment), and an unassign action
  may have ``to_user_id = NULL``.
- ``actor_user_id`` is nullable because system-triggered reassignments
  (``actor_kind='system'`` or ``'automation'``) may not have a human actor.
- ``reason`` is a short machine-readable code (see
  :data:`CANDIDATE_REASSIGNMENT_REASONS` in
  ``backend.app.services.recruiter_assignment``). Free-form human context
  belongs in ``note``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class CandidateAssigneeHistory(Base):
    __tablename__ = "candidate_assignee_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_kind: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="user"
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        Index(
            "ix_candidate_assignee_history_tenant_candidate",
            "tenant_id",
            "candidate_id",
        ),
        Index(
            "ix_candidate_assignee_history_tenant_changed",
            "tenant_id",
            "changed_at",
        ),
    )
