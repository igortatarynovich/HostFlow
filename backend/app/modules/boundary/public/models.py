"""Handoff entity types — Boundary-owned read surface."""

from __future__ import annotations

from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot

__all__ = [
    "CandidateHandoff",
    "CandidateHandoffSnapshot",
]
