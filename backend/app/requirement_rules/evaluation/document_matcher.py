"""Document fact matching for requirement alternatives (PR 2B-2)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from backend.app.document_hub.document_data_contract import DocumentDataContract
from backend.app.document_types.schema_registry import get_driver_ce_schema_bundle
from backend.app.requirement_rules.evaluation.condition_evaluator import evaluate_all_conditions
from backend.app.requirement_rules.evaluation.match_types import AlternativeMatchOutcome
from backend.app.requirement_rules.evaluation.result_contract import MatchRole, MatchedDocumentReference
from backend.app.requirement_rules.evaluation.tie_break import TieBreakCandidate, select_best_document_candidate
from backend.app.requirement_rules.requirement_rule_contract import PersonContext


def _norm(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


MATCH_ROLE_BY_REQUIREMENT: dict[str, MatchRole] = {
    "identity_document": MatchRole.identity_evidence,
    "legal_stay_confirmation": MatchRole.legal_stay_evidence,
    "labor_market_access": MatchRole.labor_access_evidence,
    "driver_entitlement": MatchRole.entitlement_evidence,
    "professional_qualification": MatchRole.qualification_evidence,
    "tachograph_eligibility": MatchRole.general_evidence,
    "medical_fitness": MatchRole.medical_evidence,
    "psychological_fitness": MatchRole.psychological_evidence,
    "driver_attestation": MatchRole.attestation_evidence,
    "work_authorization_process": MatchRole.process_evidence,
    "residence_authorization_process": MatchRole.process_evidence,
}


def match_role_for_requirement(requirement_code: str) -> MatchRole:
    return MATCH_ROLE_BY_REQUIREMENT.get(_norm(requirement_code), MatchRole.general_evidence)


def document_linked_to_entity(
    document: DocumentDataContract,
    *,
    entity_type: str,
    entity_id: str,
) -> bool:
    if not document.entity_links:
        return True
    return any(
        _norm(link.owner_type) == _norm(entity_type) and str(link.owner_id) == str(entity_id)
        for link in document.entity_links
    )


def _is_expired(document: DocumentDataContract, *, evaluation_date: date) -> bool:
    if document.valid_to is not None and document.valid_to < evaluation_date:
        return True
    return False


def _allows_perpetual_validity(document_type_code: str) -> bool:
    bundle = get_driver_ce_schema_bundle(document_type_code)
    return bool(bundle and not bundle.expiry_field)


def _to_tie_break_candidate(
    document: DocumentDataContract,
    *,
    alternative_fully_satisfied: bool,
    evaluation_date: date,
) -> TieBreakCandidate:
    return TieBreakCandidate(
        document_id=document.document_id,
        document_type_code=document.document_type_code,
        document_type_version_id=document.document_type_version_id,
        review_status=document.review_status,
        schema_valid=document.schema_valid,
        valid_to=document.valid_to,
        allows_perpetual_validity=_allows_perpetual_validity(document.document_type_code),
        review_approved_at=None,
        alternative_fully_satisfied=alternative_fully_satisfied,
        is_expired=_is_expired(document, evaluation_date=evaluation_date),
    )


def _evaluate_document_for_alternative(
    document: DocumentDataContract,
    alternative: dict,
    *,
    person: PersonContext,
    process_state: Optional[str],
    evaluation_date: date,
) -> AlternativeMatchOutcome:
    alternative_code = str(alternative.get("alternative_code") or "")
    conditions = alternative.get("conditions") or []
    cond_result = evaluate_all_conditions(
        conditions,
        document=document,
        person=person,
        process_state=process_state,
        evaluation_date=evaluation_date,
    )
    return AlternativeMatchOutcome(
        alternative_code=alternative_code,
        kind="document",
        matched=cond_result.satisfied,
        fully_satisfied=cond_result.satisfied,
        failure_reasons=cond_result.reasons,
        status_hint=cond_result.status_hint,
    )


def match_document_alternative(
    alternative: dict,
    *,
    requirement_code: str,
    documents: tuple[DocumentDataContract, ...],
    person: PersonContext,
    process_state: Optional[str],
    evaluation_date: date,
    entity_type: str,
    entity_id: str,
) -> AlternativeMatchOutcome:
    alternative_code = str(alternative.get("alternative_code") or "")
    document_type = _norm(alternative.get("document_type"))

    candidates: list[tuple[DocumentDataContract, AlternativeMatchOutcome]] = []
    tie_break_pool: list[TieBreakCandidate] = []
    outcome_by_id: dict[str, AlternativeMatchOutcome] = {}

    for document in documents:
        if _norm(document.document_type_code) != document_type:
            continue
        if _norm(document.lifecycle_status) not in {"active", ""}:
            continue
        if not document_linked_to_entity(document, entity_type=entity_type, entity_id=entity_id):
            continue

        outcome = _evaluate_document_for_alternative(
            document,
            alternative,
            person=person,
            process_state=process_state,
            evaluation_date=evaluation_date,
        )
        candidates.append((document, outcome))
        tie_break_pool.append(
            _to_tie_break_candidate(
                document,
                alternative_fully_satisfied=outcome.fully_satisfied,
                evaluation_date=evaluation_date,
            )
        )
        outcome_by_id[document.document_id] = outcome

    if not candidates:
        return AlternativeMatchOutcome(
            alternative_code=alternative_code,
            kind="document",
            matched=False,
            fully_satisfied=False,
        )

    best_doc_id = select_best_document_candidate(tie_break_pool)
    if best_doc_id is None:
        return AlternativeMatchOutcome(
            alternative_code=alternative_code,
            kind="document",
            matched=False,
            fully_satisfied=False,
        )

    best_document = next(doc for doc, _ in candidates if doc.document_id == best_doc_id.document_id)
    best_outcome = outcome_by_id[best_doc_id.document_id]

    ref = MatchedDocumentReference(
        document_id=best_document.document_id,
        document_type_code=best_document.document_type_code,
        document_type_version_id=best_document.document_type_version_id,
        review_status=best_document.review_status,
        valid_to=best_document.valid_to,
        match_role=match_role_for_requirement(requirement_code),
    )

    return AlternativeMatchOutcome(
        alternative_code=alternative_code,
        kind="document",
        matched=best_outcome.fully_satisfied,
        fully_satisfied=best_outcome.fully_satisfied,
        matched_documents=(ref,) if best_outcome.fully_satisfied else (),
        failure_reasons=best_outcome.failure_reasons,
        status_hint=best_outcome.status_hint,
    )


__all__ = [
    "document_linked_to_entity",
    "match_document_alternative",
    "match_role_for_requirement",
]
