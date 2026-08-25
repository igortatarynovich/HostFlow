"""Deterministic document candidate tie-break (ADR-018 PR 2B-1).

Pure function — no DB access. Input order must not affect the winner.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


@dataclass(frozen=True)
class TieBreakCandidate:
    document_id: str
    document_type_code: str
    document_type_version_id: Optional[str]
    review_status: str
    schema_valid: bool
    valid_to: Optional[date]
    allows_perpetual_validity: bool
    review_approved_at: Optional[datetime]
    alternative_fully_satisfied: bool
    is_expired: bool

    @property
    def is_approved(self) -> bool:
        return _norm(self.review_status) == "approved"


def _valid_to_rank(candidate: TieBreakCandidate) -> tuple[int, float]:
    """Higher rank wins.

    Perpetual (valid_to is None) is preferred only when schema allows it.
    Otherwise null valid_to is treated as incomplete — lowest rank.
    """
    if candidate.valid_to is not None:
        ordinal = candidate.valid_to.toordinal()
        return (2, float(ordinal))

    if candidate.allows_perpetual_validity:
        return (3, float("inf"))

    return (1, float("-inf"))


def _version_rank(candidate: TieBreakCandidate) -> tuple[int, str]:
    version = _norm(candidate.document_type_version_id)
    if not version:
        return (0, "")
    return (1, version)


def _review_rank(candidate: TieBreakCandidate) -> tuple[int, float]:
    if candidate.review_approved_at is None:
        return (0, float("-inf"))
    return (1, candidate.review_approved_at.timestamp())


def tie_break_sort_key(candidate: TieBreakCandidate) -> tuple:
    """Lexicographic key — max wins."""
    valid_rank = _valid_to_rank(candidate)
    version_rank = _version_rank(candidate)
    review_rank = _review_rank(candidate)
    return (
        1 if candidate.alternative_fully_satisfied else 0,
        1 if candidate.is_approved else 0,
        1 if candidate.schema_valid else 0,
        0 if candidate.is_expired else 1,
        valid_rank[0],
        valid_rank[1],
        version_rank[0],
        version_rank[1],
        review_rank[0],
        review_rank[1],
        _norm(candidate.document_id),
    )


def select_best_document_candidate(
    candidates: list[TieBreakCandidate] | tuple[TieBreakCandidate, ...],
) -> Optional[TieBreakCandidate]:
    """Pick the best candidate deterministically regardless of input order."""
    if not candidates:
        return None
    return max(candidates, key=tie_break_sort_key)


__all__ = [
    "TieBreakCandidate",
    "select_best_document_candidate",
    "tie_break_sort_key",
]
