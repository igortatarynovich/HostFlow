"""Recruitment queue: explicit assignment state (not realtime / not ingestion gate)."""

from __future__ import annotations

from typing import FrozenSet

# Persisted on ``candidates.assignment_state`` — keep values short (VARCHAR 32).
CANDIDATE_ASSIGNMENT_UNASSIGNED = "unassigned"
CANDIDATE_ASSIGNMENT_ASSIGNED = "assigned"
CANDIDATE_ASSIGNMENT_CLAIMED = "claimed"

CANDIDATE_ASSIGNMENT_VALUES: FrozenSet[str] = frozenset(
    {
        CANDIDATE_ASSIGNMENT_UNASSIGNED,
        CANDIDATE_ASSIGNMENT_ASSIGNED,
        CANDIDATE_ASSIGNMENT_CLAIMED,
    }
)


def normalize_candidate_assignment_state(raw: str | None) -> str:
    s = (raw or "").strip().lower()
    if s in CANDIDATE_ASSIGNMENT_VALUES:
        return s
    return CANDIDATE_ASSIGNMENT_UNASSIGNED
