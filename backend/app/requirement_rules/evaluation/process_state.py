"""Process requirement state model (ADR-018 PR 2B-1).

Terminal sufficiency is policy-defined — mapping requires explicit context.
"""

from __future__ import annotations

from enum import Enum

from backend.app.requirement_rules.evaluation.result_contract import RequirementEvaluationStatus


class ProcessState(str, Enum):
    not_started = "not_started"
    data_required = "data_required"
    ready_to_submit = "ready_to_submit"
    submitted = "submitted"
    authority_pending = "authority_pending"
    decision_issued = "decision_issued"
    document_issued = "document_issued"
    rejected = "rejected"
    cancelled = "cancelled"


class ProcessCompletionSufficient(str, Enum):
    """Which terminal process state satisfies the requirement."""

    decision = "decision"
    document = "document"


def map_process_state_to_requirement_status(
    process_state: ProcessState,
    *,
    completion_sufficient: ProcessCompletionSufficient,
) -> RequirementEvaluationStatus:
    """Map process state → requirement status for a policy-defined completion bar."""
    if process_state == ProcessState.not_started:
        return RequirementEvaluationStatus.missing
    if process_state == ProcessState.data_required:
        return RequirementEvaluationStatus.missing
    if process_state == ProcessState.ready_to_submit:
        return RequirementEvaluationStatus.process_pending
    if process_state in {ProcessState.submitted, ProcessState.authority_pending}:
        return RequirementEvaluationStatus.process_pending
    if process_state == ProcessState.decision_issued:
        if completion_sufficient == ProcessCompletionSufficient.decision:
            return RequirementEvaluationStatus.fulfilled
        return RequirementEvaluationStatus.process_pending
    if process_state == ProcessState.document_issued:
        return RequirementEvaluationStatus.fulfilled
    if process_state in {ProcessState.rejected, ProcessState.cancelled}:
        return RequirementEvaluationStatus.invalid
    raise ValueError(f"Unknown process state: {process_state}")


__all__ = [
    "ProcessCompletionSufficient",
    "ProcessState",
    "map_process_state_to_requirement_status",
]
