from __future__ import annotations

from datetime import date
from uuid import uuid4

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin


class CandidateEmployment(Base, TimestampMixin):
    """
    Stores compact employment history entries for a candidate.
    Used by the intake wizard to capture up to three previous jobs.
    """

    __tablename__ = "candidate_employments"
    __table_args__ = (
        Index(
            "ix_candidate_employments_tenant_candidate",
            "tenant_id",
            "candidate_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    employer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    _JSONList = MutableList.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    trailer_types: Mapped[list[str]] = mapped_column(
        _JSONList,
        nullable=False,
        default=list,
    )
    route_types: Mapped[list[str]] = mapped_column(
        _JSONList,
        nullable=False,
        default=list,
    )
    truck_brands: Mapped[list[str] | None] = mapped_column(
        _JSONList,
        nullable=True,
    )

    eu_routes: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reason_for_leaving: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_contact: Mapped[str | None] = mapped_column(Text, nullable=True)

    candidate = relationship(
        "Candidate",
        primaryjoin="CandidateEmployment.candidate_id == Candidate.id",
        viewonly=True,
    )


__all__ = ["CandidateEmployment"]
