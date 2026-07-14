"""RequirementEvaluationService input contract (ADR-018 PR 2A — evaluator in PR 2B)."""

from __future__ import annotations

from backend.app.document_hub.document_data_contract import (
    DocumentDataContract,
    RequirementEvaluationInputContract,
)

__all__ = [
    "DocumentDataContract",
    "RequirementEvaluationInputContract",
]
