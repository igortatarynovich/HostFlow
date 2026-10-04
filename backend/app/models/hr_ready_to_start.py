"""Audit of one ready_to_start.v1 decision for one Employment.

Rows are appended. A later decision does not rewrite an earlier one.
The row is not an Employment state.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base

OUTCOME_PASS = "pass"
OUTCOME_BLOCKED = "blocked"


class HrReadyToStartDecision(Base):
    __tablename__ = "hr_ready_to_start_decisions"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('pass', 'blocked')",
            name="ck_hr_ready_to_start_outcome",
        ),
        CheckConstraint(
            "legal_result IN ('pass', 'blocked') "
            "AND employee_data_result IN ('pass', 'blocked') "
            "AND terms_result IN ('pass', 'blocked') "
            "AND requirements_result IN ('pass', 'blocked')",
            name="ck_hr_ready_to_start_inputs",
        ),
        CheckConstraint(
            "(outcome = 'pass' AND legal_result = 'pass' AND employee_data_result = 'pass' "
            "AND terms_result = 'pass' AND requirements_result = 'pass' AND blocked_reasons = '[]') "
            "OR (outcome = 'blocked' AND blocked_reasons <> '[]' AND ("
            "legal_result = 'blocked' OR employee_data_result = 'blocked' "
            "OR terms_result = 'blocked' OR requirements_result = 'blocked'))",
            name="ck_hr_ready_to_start_outcome_matches_inputs",
        ),
        {"extend_existing": True},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hr_employments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    legal_result: Mapped[str] = mapped_column(String(16), nullable=False)
    legal_decision_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("hr_legal_eligibility_gate_decisions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    legal_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    employee_data_result: Mapped[str] = mapped_column(String(16), nullable=False)
    employee_data_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    terms_result: Mapped[str] = mapped_column(String(16), nullable=False)
    terms_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("hr_employment_terms.id", ondelete="RESTRICT"),
        nullable=True,
    )
    terms_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    requirements_result: Mapped[str] = mapped_column(String(16), nullable=False)
    requirements_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    blocked_reasons: Mapped[str] = mapped_column(Text, nullable=False)
