"""RequirementEvaluationService — policy-driven orchestration (ADR-018 PR 2B-2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.app.document_hub.document_data_contract import DocumentDataContract
from backend.app.requirement_rules.evaluation.alternative_matcher import match_alternative
from backend.app.requirement_rules.evaluation.fingerprint import (
    EvaluationDocumentFact,
    EvaluationFingerprintInput,
    compute_evaluation_input_fingerprint,
)
from backend.app.requirement_rules.evaluation.match_types import AlternativeMatchOutcome, RequirementMatchOutcome
from backend.app.requirement_rules.evaluation.person_fact_matcher import match_person_fact_alternative
from backend.app.requirement_rules.evaluation.result_builder import (
    build_requirement_row,
    find_alternative_definition,
)
from backend.app.requirement_rules.evaluation.result_contract import (
    OverallEvaluationStatus,
    RequirementEvaluationResult,
    RequirementEvaluationStatus,
    compute_blocking_requirements,
    compute_can_transition,
    compute_overall_status,
)
from backend.app.requirement_rules.requirement_definition_registry import get_requirement_definition_v1
from backend.app.requirement_rules.requirement_policy_registry import get_requirement_policy
from backend.app.requirement_rules.requirement_rule_contract import (
    AlternativeDisposition,
    MatchedAlternative,
    PersonContext,
    RequirementApplicability,
    RuleGraphPlanningInput,
    RuleGraphPlanningResult,
)
from backend.app.requirement_rules.requirement_rule_graph import plan_requirement_rule_graph


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


@dataclass(frozen=True)
class RequirementEvaluationRunInput:
    entity_type: str
    entity_id: str
    policy_ref: str
    target_stage: str
    evaluation_date: date
    person: PersonContext
    documents: tuple[DocumentDataContract, ...]
    process_states: dict[str, str] = field(default_factory=dict)
    overrides: dict[str, Any] = field(default_factory=dict)


_STATUS_HINT_PRIORITY = {
    RequirementEvaluationStatus.expired: 0,
    RequirementEvaluationStatus.unresolved: 1,
    RequirementEvaluationStatus.pending_review: 2,
    RequirementEvaluationStatus.process_pending: 3,
    RequirementEvaluationStatus.invalid: 4,
    RequirementEvaluationStatus.missing: 5,
}


def _pick_best_outcome(outcomes: list[AlternativeMatchOutcome]) -> Optional[AlternativeMatchOutcome]:
    fulfilled = [row for row in outcomes if row.fully_satisfied]
    if fulfilled:
        return sorted(fulfilled, key=lambda row: row.alternative_code)[0]

    if not outcomes:
        return None

    return sorted(
        outcomes,
        key=lambda row: (
            _STATUS_HINT_PRIORITY.get(row.status_hint, 99) if row.status_hint else 99,
            row.alternative_code,
        ),
    )[0]


def _match_requirement(
    requirement_code: str,
    *,
    plan: RuleGraphPlanningResult,
    documents: tuple[DocumentDataContract, ...],
    person: PersonContext,
    process_states: dict[str, str],
    evaluation_date: date,
    entity_type: str,
    entity_id: str,
) -> RequirementMatchOutcome:
    req_plan = plan.requirements.get(requirement_code)
    if req_plan is None or req_plan.applicability == RequirementApplicability.not_applicable:
        return RequirementMatchOutcome(requirement_code=requirement_code)

    definition = get_requirement_definition_v1(requirement_code)
    if not definition:
        return RequirementMatchOutcome(requirement_code=requirement_code)

    excluded_codes = {
        alt.alternative_code
        for alt in req_plan.alternatives
        if alt.disposition in {AlternativeDisposition.excluded, AlternativeDisposition.not_applicable}
    }

    outcomes: list[AlternativeMatchOutcome] = []
    for alternative in definition.get("alternatives") or []:
        if not isinstance(alternative, dict):
            continue
        alt_code = str(alternative.get("alternative_code") or "")
        if alt_code in excluded_codes:
            continue
        outcomes.append(
            match_alternative(
                alternative,
                requirement_code=requirement_code,
                documents=documents,
                person=person,
                process_states=process_states,
                evaluation_date=evaluation_date,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )

    return RequirementMatchOutcome(
        requirement_code=requirement_code,
        outcomes=outcomes,
        best=_pick_best_outcome(outcomes),
    )


def _collect_matched_alternatives(
    match_outcomes: dict[str, RequirementMatchOutcome],
) -> list[MatchedAlternative]:
    matches: list[MatchedAlternative] = []
    for req_code, outcome in sorted(match_outcomes.items()):
        if not outcome.best or not outcome.best.fully_satisfied:
            continue
        doc_id = outcome.best.matched_documents[0].document_id if outcome.best.matched_documents else None
        matches.append(
            MatchedAlternative(
                requirement_code=req_code,
                alternative_code=outcome.best.alternative_code,
                document_id=doc_id,
            )
        )

        definition = get_requirement_definition_v1(req_code)
        alt_def = None
        if definition:
            for alt in definition.get("alternatives") or []:
                if _norm(alt.get("alternative_code")) == _norm(outcome.best.alternative_code):
                    alt_def = alt
                    break
        if alt_def:
            for also_code in alt_def.get("also_satisfies") or []:
                target_req = _norm(also_code)
                target_alt = find_alternative_definition(target_req, outcome.best.alternative_code)
                if target_alt is None:
                    # Use first alternative of target requirement with same document type when possible.
                    target_definition = get_requirement_definition_v1(target_req)
                    if target_definition:
                        for candidate_alt in target_definition.get("alternatives") or []:
                            if _norm(candidate_alt.get("document_type")) == _norm(alt_def.get("document_type")):
                                target_alt_code = str(candidate_alt.get("alternative_code") or "")
                                matches.append(
                                    MatchedAlternative(
                                        requirement_code=target_req,
                                        alternative_code=target_alt_code,
                                        document_id=doc_id,
                                    )
                                )
                                break
                else:
                    matches.append(
                        MatchedAlternative(
                            requirement_code=target_req,
                            alternative_code=str(target_alt.get("alternative_code") or outcome.best.alternative_code),
                            document_id=doc_id,
                        )
                    )
    return matches


def _graph_satisfied_outcome(
    requirement_code: str,
    *,
    plan: RuleGraphPlanningResult,
    documents: tuple[DocumentDataContract, ...],
    person: PersonContext,
    process_states: dict[str, str],
    evaluation_date: date,
    entity_type: str,
    entity_id: str,
) -> Optional[AlternativeMatchOutcome]:
    req_plan = plan.requirements.get(requirement_code)
    if req_plan is None:
        return None
    for alt in req_plan.alternatives:
        if alt.disposition != AlternativeDisposition.matched:
            continue
        alt_def = find_alternative_definition(requirement_code, alt.alternative_code)
        if not alt_def:
            continue
        kind = _norm(alt_def.get("kind"))
        if kind == "person_fact":
            return match_person_fact_alternative(
                alt_def,
                person=person,
                process_state=process_states.get(requirement_code),
                evaluation_date=evaluation_date,
            )
        if kind == "document":
            return match_alternative(
                alt_def,
                requirement_code=requirement_code,
                documents=documents,
                person=person,
                process_states=process_states,
                evaluation_date=evaluation_date,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        if kind == "process_state":
            return match_alternative(
                alt_def,
                requirement_code=requirement_code,
                documents=documents,
                person=person,
                process_states=process_states,
                evaluation_date=evaluation_date,
                entity_type=entity_type,
                entity_id=entity_id,
            )
    return None


def _build_fingerprint_input(inp: RequirementEvaluationRunInput, *, policy_version: str) -> EvaluationFingerprintInput:
    doc_facts = tuple(
        EvaluationDocumentFact(
            document_id=doc.document_id,
            document_type_code=doc.document_type_code,
            document_type_version_id=doc.document_type_version_id,
            review_status=doc.review_status,
            valid_to=doc.valid_to,
            schema_valid=doc.schema_valid,
            lifecycle_status=doc.lifecycle_status,
            document_data=dict(doc.document_data),
        )
        for doc in inp.documents
    )
    return EvaluationFingerprintInput(
        policy_ref=inp.policy_ref,
        policy_version=policy_version,
        target_stage=inp.target_stage,
        person_facts={
            "citizenship": inp.person.citizenship,
            "international_haulage": inp.person.international_haulage,
            "community_licence_carrier": inp.person.community_licence_carrier,
        },
        documents=doc_facts,
        process_states=dict(inp.process_states),
        overrides=dict(inp.overrides),
    )


def evaluate_requirements(inp: RequirementEvaluationRunInput) -> RequirementEvaluationResult:
    """Run one policy-driven requirement evaluation."""
    policy = get_requirement_policy(inp.policy_ref)
    if not policy:
        raise ValueError(f"unknown policy_ref: {inp.policy_ref}")
    policy_version = str(policy.get("policy_version") or "unknown")

    graph_input = RuleGraphPlanningInput(
        policy_ref=inp.policy_ref,
        person=inp.person,
        target_stage=inp.target_stage,
        evaluation_date=inp.evaluation_date,
        matched_alternatives=(),
    )
    initial_plan = plan_requirement_rule_graph(graph_input)

    match_outcomes: dict[str, RequirementMatchOutcome] = {}
    for requirement_code in sorted(initial_plan.requirements.keys()):
        req_plan = initial_plan.requirements[requirement_code]
        if req_plan.applicability == RequirementApplicability.not_applicable:
            continue
        match_outcomes[requirement_code] = _match_requirement(
            requirement_code,
            plan=initial_plan,
            documents=inp.documents,
            person=inp.person,
            process_states=inp.process_states,
            evaluation_date=inp.evaluation_date,
            entity_type=inp.entity_type,
            entity_id=inp.entity_id,
        )

    matched_alternatives = tuple(_collect_matched_alternatives(match_outcomes))
    final_plan = plan_requirement_rule_graph(
        RuleGraphPlanningInput(
            policy_ref=inp.policy_ref,
            person=inp.person,
            target_stage=inp.target_stage,
            evaluation_date=inp.evaluation_date,
            matched_alternatives=matched_alternatives,
        )
    )

    rows = []
    for requirement_code in sorted(final_plan.requirements.keys()):
        plan_row = final_plan.requirements[requirement_code]
        match = match_outcomes.get(requirement_code)
        graph_outcome = _graph_satisfied_outcome(
            requirement_code,
            plan=final_plan,
            documents=inp.documents,
            person=inp.person,
            process_states=inp.process_states,
            evaluation_date=inp.evaluation_date,
            entity_type=inp.entity_type,
            entity_id=inp.entity_id,
        )
        rows.append(
            build_requirement_row(
                plan=plan_row,
                match=match,
                graph_matched_outcome=graph_outcome,
                person=inp.person,
                target_stage=inp.target_stage,
            )
        )

    requirements = tuple(rows)
    can_transition = compute_can_transition(requirements)
    overall_status = compute_overall_status(requirements, can_transition=can_transition)
    fingerprint = compute_evaluation_input_fingerprint(
        _build_fingerprint_input(inp, policy_version=policy_version)
    )

    return RequirementEvaluationResult(
        entity_type=inp.entity_type,
        entity_id=inp.entity_id,
        policy_ref=inp.policy_ref,
        policy_version=policy_version,
        target_stage=_norm(inp.target_stage),
        evaluated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        input_fingerprint=fingerprint,
        overall_status=overall_status,
        can_transition=can_transition,
        blocking_requirements=compute_blocking_requirements(requirements),
        requirements=requirements,
    )


__all__ = [
    "RequirementEvaluationRunInput",
    "evaluate_requirements",
]
