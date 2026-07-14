"""Process requirement matching (PR 2B-2)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.requirement_rules.evaluation.condition_evaluator import evaluate_all_conditions
from backend.app.requirement_rules.evaluation.match_types import AlternativeMatchOutcome
from backend.app.requirement_rules.evaluation.process_state import (
    ProcessCompletionSufficient,
    ProcessState,
    map_process_state_to_requirement_status,
)
from backend.app.requirement_rules.evaluation.result_contract import (
    MatchedProcessReference,
    RequirementEvaluationStatus,
)
from backend.app.requirement_rules.requirement_rule_contract import PersonContext


POLICY_TO_PROCESS_STATE: dict[str, ProcessState] = {
    "not_started": ProcessState.not_started,
    "data_required": ProcessState.data_required,
    "ready_to_submit": ProcessState.ready_to_submit,
    "application_submitted": ProcessState.submitted,
    "submitted": ProcessState.submitted,
    "in_progress": ProcessState.authority_pending,
    "authority_pending": ProcessState.authority_pending,
    "decision_issued": ProcessState.decision_issued,
    "document_issued": ProcessState.document_issued,
    "rejected": ProcessState.rejected,
    "cancelled": ProcessState.cancelled,
}


def _norm(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def resolve_process_state(raw: Optional[str]) -> Optional[ProcessState]:
    if not raw:
        return None
    return POLICY_TO_PROCESS_STATE.get(_norm(raw))


def process_completion_sufficient_for_requirement(requirement_code: str, alternative: dict) -> ProcessCompletionSufficient:
    kind = _norm(alternative.get("kind"))
    alt_code = _norm(alternative.get("alternative_code"))
    if kind == "document":
        return ProcessCompletionSufficient.document
    if "decision" in alt_code:
        return ProcessCompletionSufficient.decision
    if requirement_code in {"work_authorization_process", "residence_authorization_process"}:
        return ProcessCompletionSufficient.decision
    return ProcessCompletionSufficient.document


def match_process_alternative(
    alternative: dict,
    *,
    requirement_code: str,
    person: PersonContext,
    process_state: Optional[str],
    evaluation_date: date,
) -> AlternativeMatchOutcome:
    alternative_code = str(alternative.get("alternative_code") or "")
    conditions = alternative.get("conditions") or []
    cond_result = evaluate_all_conditions(
        conditions,
        document=None,
        person=person,
        process_state=process_state,
        evaluation_date=evaluation_date,
    )

    resolved = resolve_process_state(process_state)
    status_hint: Optional[RequirementEvaluationStatus] = cond_result.status_hint
    if resolved is not None:
        completion = process_completion_sufficient_for_requirement(requirement_code, alternative)
        status_hint = map_process_state_to_requirement_status(resolved, completion_sufficient=completion)

    process_ref = None
    if process_state:
        process_ref = MatchedProcessReference(
            process_code=requirement_code,
            process_state=str(process_state),
            requirement_code=requirement_code,
        )

    return AlternativeMatchOutcome(
        alternative_code=alternative_code,
        kind="process_state",
        matched=cond_result.satisfied,
        fully_satisfied=cond_result.satisfied,
        matched_process=process_ref,
        failure_reasons=cond_result.reasons,
        status_hint=status_hint,
    )


__all__ = [
    "match_process_alternative",
    "process_completion_sufficient_for_requirement",
    "resolve_process_state",
]
