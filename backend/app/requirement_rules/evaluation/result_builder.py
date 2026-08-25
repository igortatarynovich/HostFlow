"""Build RequirementEvaluationResult DTO rows (PR 2B-2)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from backend.app.constants.stages import PIPELINE_SEQUENCE
from backend.app.requirement_rules.evaluation.match_types import AlternativeMatchOutcome, RequirementMatchOutcome
from backend.app.requirement_rules.evaluation.result_contract import (
    EvaluationReason,
    EvaluationReasonCode,
    EvaluationReasonSeverity,
    EvaluationReasonSourceType,
    ExcludedAlternative,
    NextActionCode,
    RequirementApplicability,
    RequirementEvaluationRow,
    RequirementEvaluationStatus,
    RequirementOwnership,
    compute_is_blocking,
)
from backend.app.requirement_rules.requirement_definition_registry import get_requirement_definition_v1
from backend.app.requirement_rules.requirement_rule_contract import (
    AlternativeDisposition,
    PersonContext,
    RequirementPlan,
    StageOwnership,
)
from backend.app.requirement_rules.citizenship import citizenship_segment
from backend.app.requirement_rules.requirement_rule_contract import CitizenshipSegment


IMMIGRATION_REQUIREMENT_CODES = frozenset(
    {
        "legal_stay_confirmation",
        "labor_market_access",
        "work_authorization_process",
        "residence_authorization_process",
    }
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _stage_index(stage: Optional[str]) -> int:
    code = _norm(stage)
    if code in PIPELINE_SEQUENCE:
        return PIPELINE_SEQUENCE.index(code)
    return -1


def is_not_required_yet(*, required_by_stage: Optional[str], target_stage: str) -> bool:
    req_idx = _stage_index(required_by_stage)
    tgt_idx = _stage_index(target_stage)
    if req_idx < 0 or tgt_idx < 0:
        return False
    return tgt_idx < req_idx


def _ownership_from_stage(stage: Optional[StageOwnership]) -> Optional[RequirementOwnership]:
    if stage is None:
        return None
    return RequirementOwnership(
        source_responsibility=stage.source_responsibility,
        operational_owner=stage.operational_owner,
        verification_role=stage.verification_role,
        acquisition_mode=stage.acquisition_mode,
    )


def _next_action_for_status(
    status: RequirementEvaluationStatus,
    *,
    requirement_code: str,
    has_unclassified_hint: bool = False,
) -> NextActionCode:
    if status == RequirementEvaluationStatus.fulfilled:
        return NextActionCode.none
    if status == RequirementEvaluationStatus.unresolved:
        return NextActionCode.resolve_person_context
    if status == RequirementEvaluationStatus.pending_review:
        return NextActionCode.review_document
    if status == RequirementEvaluationStatus.process_pending:
        return NextActionCode.await_authority
    if status == RequirementEvaluationStatus.invalid:
        return NextActionCode.upload_document
    if status == RequirementEvaluationStatus.expired:
        return NextActionCode.upload_document
    if has_unclassified_hint:
        return NextActionCode.classify_document
    if requirement_code.endswith("_process"):
        return NextActionCode.start_process
    return NextActionCode.upload_document


def _graph_matched_alternative_code(plan: RequirementPlan) -> Optional[str]:
    for alt in plan.alternatives:
        if alt.disposition == AlternativeDisposition.matched:
            return alt.alternative_code
    return None


def _excluded_from_plan(plan: RequirementPlan) -> tuple[ExcludedAlternative, ...]:
    rows: list[ExcludedAlternative] = []
    for alt in plan.alternatives:
        if alt.disposition == AlternativeDisposition.excluded:
            rows.append(
                ExcludedAlternative(
                    alternative_code=alt.alternative_code,
                    disposition="excluded",
                    reason_code=EvaluationReasonCode.alternative_excluded,
                )
            )
        elif alt.disposition == AlternativeDisposition.not_selected:
            rows.append(
                ExcludedAlternative(
                    alternative_code=alt.alternative_code,
                    disposition="not_selected",
                    reason_code=EvaluationReasonCode.policy_condition_not_met,
                )
            )
    return tuple(rows)


def _resolve_applicability(
    plan: RequirementPlan,
    *,
    person: PersonContext,
    match: Optional[RequirementMatchOutcome],
) -> RequirementApplicability:
    if plan.applicability.value == RequirementApplicability.not_applicable.value:
        return RequirementApplicability.not_applicable

    segment = citizenship_segment(person.citizenship)
    if segment == CitizenshipSegment.unknown and _norm(plan.requirement_code) in IMMIGRATION_REQUIREMENT_CODES:
        if match is None or not (match.best and match.best.fully_satisfied):
            return RequirementApplicability.unresolved
    return RequirementApplicability.applicable


def build_requirement_row(
    *,
    plan: RequirementPlan,
    match: Optional[RequirementMatchOutcome],
    graph_matched_outcome: Optional[AlternativeMatchOutcome],
    person: PersonContext,
    target_stage: str,
) -> RequirementEvaluationRow:
    requirement_code = plan.requirement_code
    ownership = plan.stage_ownership
    required_by_stage = ownership.required_by_stage if ownership else None
    blocks_stage = ownership.blocks_stage if ownership else None

    applicability = _resolve_applicability(plan, person=person, match=match)
    excluded = _excluded_from_plan(plan)

    if applicability == RequirementApplicability.not_applicable:
        status = RequirementEvaluationStatus.not_applicable
        return RequirementEvaluationRow(
            requirement_code=requirement_code,
            applicability=applicability,
            status=status,
            is_blocking=compute_is_blocking(
                applicability=applicability,
                status=status,
                blocks_stage=blocks_stage,
                target_stage=target_stage,
            ),
            required_by_stage=required_by_stage,
            blocks_stage=blocks_stage,
            matched_alternative=None,
            matched_documents=(),
            matched_person_facts=(),
            matched_process=None,
            excluded_alternatives=excluded,
            missing_fields=(),
            reasons=(),
            ownership=_ownership_from_stage(ownership),
            next_action=NextActionCode.none,
        )

    if applicability == RequirementApplicability.unresolved:
        status = RequirementEvaluationStatus.unresolved
        reasons = (
            EvaluationReason(
                code=EvaluationReasonCode.citizenship_unknown,
                message_key="requirement.person.citizenship_unknown",
                severity=EvaluationReasonSeverity.blocker,
                source_type=EvaluationReasonSourceType.person,
                source_ref="platform.identity.citizenship",
            ),
        )
        return RequirementEvaluationRow(
            requirement_code=requirement_code,
            applicability=applicability,
            status=status,
            is_blocking=compute_is_blocking(
                applicability=applicability,
                status=status,
                blocks_stage=blocks_stage,
                target_stage=target_stage,
            ),
            required_by_stage=required_by_stage,
            blocks_stage=blocks_stage,
            matched_alternative=None,
            matched_documents=(),
            matched_person_facts=(),
            matched_process=None,
            excluded_alternatives=excluded,
            missing_fields=(),
            reasons=reasons,
            ownership=_ownership_from_stage(ownership),
            next_action=NextActionCode.resolve_person_context,
        )

    if is_not_required_yet(required_by_stage=required_by_stage, target_stage=target_stage):
        status = RequirementEvaluationStatus.not_required_yet
        return RequirementEvaluationRow(
            requirement_code=requirement_code,
            applicability=RequirementApplicability.applicable,
            status=status,
            is_blocking=compute_is_blocking(
                applicability=RequirementApplicability.applicable,
                status=status,
                blocks_stage=blocks_stage,
                target_stage=target_stage,
            ),
            required_by_stage=required_by_stage,
            blocks_stage=blocks_stage,
            matched_alternative=None,
            matched_documents=(),
            matched_person_facts=(),
            matched_process=None,
            excluded_alternatives=excluded,
            missing_fields=(),
            reasons=(),
            ownership=_ownership_from_stage(ownership),
            next_action=NextActionCode.none,
        )

    best = match.best if match else None
    if graph_matched_outcome and graph_matched_outcome.fully_satisfied:
        best = graph_matched_outcome
    elif best is None and graph_matched_outcome:
        best = graph_matched_outcome

    graph_alt = _graph_matched_alternative_code(plan)

    if best and best.fully_satisfied:
        status = RequirementEvaluationStatus.fulfilled
        if best.status_hint == RequirementEvaluationStatus.process_pending:
            status = RequirementEvaluationStatus.process_pending
        return RequirementEvaluationRow(
            requirement_code=requirement_code,
            applicability=RequirementApplicability.applicable,
            status=status,
            is_blocking=compute_is_blocking(
                applicability=RequirementApplicability.applicable,
                status=status,
                blocks_stage=blocks_stage,
                target_stage=target_stage,
            ),
            required_by_stage=required_by_stage,
            blocks_stage=blocks_stage,
            matched_alternative=best.alternative_code or graph_alt,
            matched_documents=best.matched_documents,
            matched_person_facts=best.matched_person_facts,
            matched_process=best.matched_process,
            excluded_alternatives=excluded,
            missing_fields=(),
            reasons=(),
            ownership=_ownership_from_stage(ownership),
            next_action=_next_action_for_status(status, requirement_code=requirement_code),
        )

    status = RequirementEvaluationStatus.missing
    reasons: tuple[EvaluationReason, ...] = ()
    missing_fields: tuple[str, ...] = ()
    if best:
        if best.status_hint:
            status = best.status_hint
        reasons = best.failure_reasons
        for reason in reasons:
            for field_name in reason.details.get("field", ""), *reason.details.get("missing_fields", []):
                if field_name:
                    missing_fields = (*missing_fields, str(field_name))

    if graph_alt and any(
        alt.disposition == AlternativeDisposition.excluded for alt in plan.alternatives
    ) and status == RequirementEvaluationStatus.missing:
        # Excluded alternatives alone must not surface as missing when another path exists.
        pass

    return RequirementEvaluationRow(
        requirement_code=requirement_code,
        applicability=RequirementApplicability.applicable,
        status=status,
        is_blocking=compute_is_blocking(
            applicability=RequirementApplicability.applicable,
            status=status,
            blocks_stage=blocks_stage,
            target_stage=target_stage,
        ),
        required_by_stage=required_by_stage,
        blocks_stage=blocks_stage,
        matched_alternative=None,
        matched_documents=best.matched_documents if best else (),
        matched_person_facts=(),
        matched_process=best.matched_process if best else None,
        excluded_alternatives=excluded,
        missing_fields=missing_fields,
        reasons=reasons,
        ownership=_ownership_from_stage(ownership),
        next_action=_next_action_for_status(status, requirement_code=requirement_code),
    )


def find_alternative_definition(requirement_code: str, alternative_code: str) -> Optional[dict]:
    definition = get_requirement_definition_v1(requirement_code)
    if not definition:
        return None
    target = _norm(alternative_code)
    for alt in definition.get("alternatives") or []:
        if isinstance(alt, dict) and _norm(alt.get("alternative_code")) == target:
            return alt
    return None


__all__ = [
    "IMMIGRATION_REQUIREMENT_CODES",
    "build_requirement_row",
    "find_alternative_definition",
    "is_not_required_yet",
]
