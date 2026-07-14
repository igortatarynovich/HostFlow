"""Candidate → RequirementEvaluationRunInput bridge (PR 2B-3 cutover adapter)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.document_hub.document_data_contract import (
    DocumentDataContract,
    build_document_data_contract_from_hub_row,
)
from backend.app.models.candidate import Candidate
from backend.app.modules.documents.crud import list_candidate_documents
from backend.app.requirement_rules.evaluation.service import (
    RequirementEvaluationRunInput,
    evaluate_requirements,
)
from backend.app.requirement_rules.evaluation.result_contract import RequirementEvaluationResult
from backend.app.requirement_rules.requirement_policy_registry import (
    ENTITY_PROFILE_TO_DEFAULT_POLICY,
    get_requirement_policy,
)
from backend.app.requirement_rules.requirement_rule_contract import PersonContext
from backend.app.services.requirement_policy_assignment import resolve_policy_ref_for_candidate


def _candidate_extra(candidate: Candidate) -> dict[str, Any]:
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    return extra if isinstance(extra, dict) else {}


def _candidate_personal(candidate: Candidate) -> dict[str, Any]:
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    return personal if isinstance(personal, dict) else {}


def _build_person_context(candidate: Candidate) -> PersonContext:
    extra = _candidate_extra(candidate)
    personal = _candidate_personal(candidate)
    return PersonContext(
        citizenship=extra.get("citizenship") or personal.get("citizenship"),
        international_haulage=bool(extra.get("international_haulage")),
        community_licence_carrier=bool(extra.get("community_licence_carrier")),
        employment_country=str(extra.get("work_country") or personal.get("work_country") or "PL"),
    )


def _process_states_from_candidate(candidate: Candidate) -> dict[str, str]:
    extra = _candidate_extra(candidate)
    raw = extra.get("requirement_process_states")
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return {}


async def load_document_data_contracts_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> tuple[DocumentDataContract, ...]:
    docs = await list_candidate_documents(
        db,
        tenant_id,
        candidate_id,
        include_deleted=False,
    )
    contracts: list[DocumentDataContract] = []
    for doc in docs:
        if getattr(doc, "deleted_at", None) is not None:
            continue
        contracts.append(build_document_data_contract_from_hub_row(doc))
    return tuple(contracts)


async def evaluate_candidate_requirements_v2(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    target_stage: str,
    evaluation_date: Optional[date] = None,
) -> RequirementEvaluationResult:
    policy_ref = await resolve_policy_ref_for_candidate(
        db,
        tenant_id=str(tenant_id),
        candidate=candidate,
    )
    if not policy_ref:
        entity_profile = str(getattr(candidate, "entity_profile_code", "") or "")
        policy_ref = ENTITY_PROFILE_TO_DEFAULT_POLICY.get(entity_profile)
    if not policy_ref or not get_requirement_policy(policy_ref):
        raise ValueError(f"No requirement policy for candidate {candidate.id}")

    documents = await load_document_data_contracts_for_candidate(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate.id),
    )
    run_input = RequirementEvaluationRunInput(
        entity_type="candidate",
        entity_id=str(candidate.id),
        policy_ref=policy_ref,
        target_stage=target_stage,
        evaluation_date=evaluation_date or date.today(),
        person=_build_person_context(candidate),
        documents=documents,
        process_states=_process_states_from_candidate(candidate),
    )
    return evaluate_requirements(run_input)


__all__ = [
    "evaluate_candidate_requirements_v2",
    "load_document_data_contracts_for_candidate",
]
