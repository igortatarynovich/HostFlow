"""Hiring Acceptance Contract — frozen walk classification (HE-1).

Contract id: ``hiring_acceptance.v1``.

One operator question. Nine walk steps. Dual-evidence disposition sealed.
Admissible production evidence named. Forbidden implementation frozen.

Not HE-2 stage consumption. Not HE-3 eligibility collapse. Not HE-4 / RS-7
execution. Not min HR. Not a new Hiring Product, stage machine, funnel
builder, or workflow engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

CONTRACT_ID: Final[str] = "hiring_acceptance.v1"

OPERATOR_QUESTION: Final[str] = (
    "for one candidate on an operator-configured tenant, "
    "which authority answers each step of "
    "stage → requirements/docs → eligibility → transfer, "
    "what is the candidate_evidence ↔ Document Link disposition, "
    "and what evidence is admissible as production proof of that walk?"
)

WALK_PHASES: Final[tuple[str, ...]] = (
    "stage",
    "requirements_docs",
    "eligibility",
    "transfer",
)

EVIDENCE_DISPOSITION: Final[str] = "candidate_evidence_binds_document_link"

HeRole = Literal[
    "authority",
    "consume",
    "leftover",
    "compose_later",
    "not_this_walk",
]

CLOSED_ROLES: Final[frozenset[str]] = frozenset(
    {
        "authority",
        "consume",
        "leftover",
        "compose_later",
        "not_this_walk",
    }
)


@dataclass(frozen=True)
class WalkStep:
    code: str
    phase: str
    operator_question: str
    authority: str
    authority_role: HeRole
    authority_paths: tuple[str, ...]
    later_slice: str


WALK_STEPS: Final[tuple[WalkStep, ...]] = (
    WalkStep(
        code="stage_existence",
        phase="stage",
        operator_question="which stages exist for this hiring path?",
        authority="li1_is_stage_registered",
        authority_role="authority",
        authority_paths=("backend/app/platform/module_stage_registry/existence.py",),
        later_slice="none",
    ),
    WalkStep(
        code="stage_occupancy",
        phase="stage",
        operator_question="which stage is this candidate on?",
        authority="candidate_occupancy",
        authority_role="authority",
        authority_paths=("backend/app/models/candidate.py",),
        later_slice="none",
    ),
    WalkStep(
        code="stage_transition",
        phase="stage",
        operator_question="may this candidate move from stage A to stage B?",
        authority="transition_order_rule",
        authority_role="authority",
        authority_paths=("backend/app/reference/hiring_stage_authority.py",),
        later_slice="none",
    ),
    WalkStep(
        code="requirement_policy",
        phase="requirements_docs",
        operator_question="must this candidate provide document type X?",
        authority="requirement_policy_authority_v1",
        authority_role="authority",
        authority_paths=(
            "backend/app/reference/requirement_policy_authority.py",
            "backend/app/reference/document_policy_merge.py",
        ),
        later_slice="none",
    ),
    WalkStep(
        code="document_request",
        phase="requirements_docs",
        operator_question="what outstanding document ask exists for this candidate?",
        authority="hub_outstanding_ask",
        authority_role="authority",
        authority_paths=(
            "backend/app/requirement_rules/engine_to_hub_outstanding_ask_contract.py",
            "backend/app/services/document_hub_delivery_contract.py",
        ),
        later_slice="none",
    ),
    WalkStep(
        code="document_instance",
        phase="requirements_docs",
        operator_question="does a Hub document instance exist, and is it valid?",
        authority="document_link",
        authority_role="authority",
        authority_paths=("backend/app/models/document_entity_link.py",),
        later_slice="none",
    ),
    WalkStep(
        code="requirement_satisfaction",
        phase="requirements_docs",
        operator_question="is requirement R satisfied for this candidate?",
        authority="candidate_evidence_bound_to_document_link",
        authority_role="authority",
        authority_paths=("backend/app/services/candidate_evidence_service.py",),
        later_slice="none",
    ),
    WalkStep(
        code="eligibility_decision",
        phase="eligibility",
        operator_question="may this candidate transfer, and with what readable reason if not?",
        authority="rpm_result_plus_he3_composer",
        authority_role="compose_later",
        authority_paths=("backend/app/services/transfer_policy_resolver.py",),
        later_slice="he-3",
    ),
    WalkStep(
        code="transfer_complete",
        phase="transfer",
        operator_question="is the Recruitment hire complete?",
        authority="ready_for_employment_v1_emit",
        authority_role="authority",
        authority_paths=("backend/app/reference/ready_for_employment.py",),
        later_slice="he-4",
    ),
)


@dataclass(frozen=True)
class ClassifiedAnswerer:
    code: str
    role: HeRole
    paths: tuple[str, ...]


STAGE_EXISTENCE_LEFTOVERS: Final[tuple[ClassifiedAnswerer, ...]] = (
    ClassifiedAnswerer(
        code="static_new_to_hired_list",
        role="leftover",
        paths=(
            "backend/app/constants/stages.py",
            "backend/app/api/v1/stages.py",
        ),
    ),
    ClassifiedAnswerer(
        code="tenant_candidate_stages_dictionary",
        role="leftover",
        paths=("backend/app/models/candidate_stage.py",),
    ),
    ClassifiedAnswerer(
        code="funnel_stages_as_existence",
        role="leftover",
        paths=("backend/app/models/funnel.py",),
    ),
)

ELIGIBILITY_ANSWERERS: Final[tuple[ClassifiedAnswerer, ...]] = (
    ClassifiedAnswerer(
        code="transfer_policy_composer",
        role="leftover",
        paths=("backend/app/services/transfer_policy_resolver.py",),
    ),
    ClassifiedAnswerer(
        code="workforce_packs",
        role="leftover",
        paths=("backend/app/services/workforce_eligibility_delivery_contract.py",),
    ),
    ClassifiedAnswerer(
        code="package_readiness",
        role="leftover",
        paths=("backend/app/services/recruitment_package_readiness.py",),
    ),
    ClassifiedAnswerer(
        code="field_requirements",
        role="leftover",
        paths=("backend/app/field_registry/requirement_evaluator.py",),
    ),
    ClassifiedAnswerer(
        code="requirement_rules_v1",
        role="leftover",
        paths=("backend/app/requirement_rules/evaluator.py",),
    ),
    ClassifiedAnswerer(
        code="requirement_rules_v2",
        role="leftover",
        paths=("backend/app/requirement_rules/evaluation/candidate_bridge.py",),
    ),
    ClassifiedAnswerer(
        code="operational_requirements",
        role="consume",
        paths=("backend/app/services/transfer_policy_resolver.py",),
    ),
    ClassifiedAnswerer(
        code="handoff_routing",
        role="leftover",
        paths=("backend/app/services/transfer_policy_resolver.py",),
    ),
    ClassifiedAnswerer(
        code="pipeline_gates",
        role="leftover",
        paths=("backend/app/services/hiring_pipeline_gates.py",),
    ),
    ClassifiedAnswerer(
        code="legacy_doc_type_blockers",
        role="leftover",
        paths=("backend/app/services/candidate_doc_pipeline_guard.py",),
    ),
)

ADMISSIBLE_EVIDENCE: Final[tuple[str, ...]] = (
    "rs1_operator_configured_tenant",
    "product_surface_stage_moves",
    "product_surface_document_request_provide_accept",
    "document_link_row",
    "candidate_evidence_bound_to_document_link",
    "operator_readable_refusal_from_rpm",
    "stage_history",
    "transfer_completion_record",
)

INADMISSIBLE_EVIDENCE: Final[tuple[str, ...]] = (
    "seed_documents_for_ready_for_handoff",
    "candidate_evidence_helpers",
    "sql_or_fixture_document_insert",
    "get_transfer_readiness_as_proof",
    "http_409_without_readable_reason",
)

INADMISSIBLE_EVIDENCE_PATHS: Final[tuple[str, ...]] = (
    "backend/tests/test_support/candidate_handoff_gate.py",
    "backend/tests/test_support/candidate_evidence_helpers.py",
)

FORBIDDEN_IMPLEMENTATION: Final[tuple[str, ...]] = (
    "new_hiring_product",
    "new_stage_machine",
    "funnel_builder",
    "workflow_engine",
    "auto_progression",
    "min_hr_handoff",
    "he2_runtime_in_this_pr",
    "he3_collapse_in_this_pr",
    "rs7_execution",
    "inherited_dr1_mapping_red_fix",
    "hiring_eligibility_outside_rpm",
    "tenth_rpm_write",
    "candidate_evidence_as_file_store",
    "document_link_as_requirement_policy",
)


def walk_step_codes() -> tuple[str, ...]:
    return tuple(step.code for step in WALK_STEPS)


def authority_steps() -> tuple[WalkStep, ...]:
    return tuple(step for step in WALK_STEPS if step.authority_role == "authority")
