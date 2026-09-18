"""RequirementEvaluationService input contract (ADR-018 PR 2A — evaluator in PR 2B)."""

from __future__ import annotations

from backend.app.modules.documents.public.evidence import (
    DocumentDataContract,
    RequirementEvaluationInputContract,
)

__all__ = [
    "DocumentDataContract",
    "RequirementEvaluationInputContract",
]
