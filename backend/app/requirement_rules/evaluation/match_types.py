"""Internal types for requirement evaluation matching (PR 2B-2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.app.requirement_rules.evaluation.result_contract import (
    EvaluationReason,
    ExcludedAlternative,
    MatchedDocumentReference,
    MatchedProcessReference,
    RequirementEvaluationStatus,
)


@dataclass(frozen=True)
class AlternativeMatchOutcome:
    alternative_code: str
    kind: str
    matched: bool
    fully_satisfied: bool
    matched_documents: tuple[MatchedDocumentReference, ...] = ()
    matched_person_facts: tuple[str, ...] = ()
    matched_process: Optional[MatchedProcessReference] = None
    failure_reasons: tuple[EvaluationReason, ...] = ()
    status_hint: Optional[RequirementEvaluationStatus] = None


@dataclass
class RequirementMatchOutcome:
    requirement_code: str
    outcomes: list[AlternativeMatchOutcome] = field(default_factory=list)
    best: Optional[AlternativeMatchOutcome] = None
    excluded_alternatives: list[ExcludedAlternative] = field(default_factory=list)


__all__ = [
    "AlternativeMatchOutcome",
    "RequirementMatchOutcome",
]
