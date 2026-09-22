"""Hiring Stage Authority Consumption — production stage walk (HE-2).

Contract id: ``hiring_stage_authority.v1``.

Consumes ``hiring_acceptance.v1`` stage steps. Existence comes from LI-1
``is_stage_registered``. Occupancy stays ``Candidate.stage``. Transition
order is the production rule ``forward_moves_guarded_jumps_rejected``.

Not HE-3 eligibility collapse. Not HE-4 / RS-7. Not min HR. Not LI-2+.
Not a new Hiring Product or stage machine.
"""

from __future__ import annotations

from typing import Final, Literal

from fastapi import HTTPException

from backend.app.platform.module_stage_registry import is_stage_registered

from backend.app.reference.hiring_acceptance import (
    CONTRACT_ID as HIRING_ACCEPTANCE_CONTRACT_ID,
    STAGE_EXISTENCE_LEFTOVERS,
)

CONTRACT_ID: Final[str] = "hiring_stage_authority.v1"
PARENT_CONTRACT_ID: Final[str] = HIRING_ACCEPTANCE_CONTRACT_ID

EXISTENCE_API: Final[str] = "is_stage_registered"
EXISTENCE_MODULE: Final[str] = "recruitment"
EXISTENCE_ENTITY: Final[str] = "candidate"
OCCUPANCY_AUTHORITY: Final[str] = "candidate_stage"
TRANSITION_RULE: Final[str] = "forward_moves_guarded_jumps_rejected"

TransitionKind = Literal["same", "forward", "backward", "jump"]

# Unique hiring-path order of LI-1 keys. Used to classify forward vs back.
# Not a new stage machine: every key must already be registered.
TRANSITION_ORDER: Final[tuple[str, ...]] = (
    "new",
    "no_answer",
    "contacted",
    "questionnaire_submitted",
    "docs_wait",
    "docs_got",
    "permit_ordered",
    "permit_received",
    "visa",
    "red_paper",
    "trip_plan",
    "at_client",
    "employment_pending",
    "on_trip",
    "probation_ok",
    "employed",
    "rejected",
    "declined",
    "ready_for_handoff",
    "ready_for_hr",
    "processing_by_hr",
    "hired",
    "processing_by_client",
    "docs_submitted_permit",
    "handoff_returned",
)

STAGE_ALIASES: Final[dict[str, str]] = {
    "planning_arrival": "trip_plan",
    "plan_arrival": "trip_plan",
    "planning-trip": "trip_plan",
    "contact_established": "contacted",
    "interview": "contacted",
}

HIRING_PATH_EXISTENCE_CONSUMERS: Final[tuple[str, ...]] = (
    "backend/app/api/v1/candidates/helpers.py",
    "backend/app/api/v1/candidates/service.py",
    "backend/app/services/candidate_doc_pipeline_guard.py",
)

EXISTENCE_PRODUCER: Final[str] = (
    "backend/app/platform/module_stage_registry/existence.py"
)

FORBIDDEN_IMPLEMENTATION: Final[tuple[str, ...]] = (
    "new_hiring_product",
    "new_stage_machine",
    "funnel_builder",
    "workflow_engine",
    "auto_progression",
    "min_hr_handoff",
    "he3_collapse_in_this_pr",
    "rs7_execution",
    "inherited_dr1_mapping_red_fix",
    "requirements_docs_disposition_reopen",
    "leftover_file_deletion",
    "li2_lifecycle_cutover",
    "funnel_ui_rework",
    "universalize_funnel_stage_code",
    "meta_stages_cutover",
)


def leftover_existence_codes() -> tuple[str, ...]:
    return tuple(row.code for row in STAGE_EXISTENCE_LEFTOVERS)


def hiring_stage_exists(stage_key: str) -> bool:
    key = str(stage_key or "").strip().lower()
    if not key:
        return False
    return is_stage_registered(EXISTENCE_MODULE, EXISTENCE_ENTITY, key)


def normalize_hiring_stage_key(raw: str | None) -> str | None:
    """Map occupancy spelling onto a registered key. Leftovers do not grant existence."""
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    lower = text.lower()
    alias = STAGE_ALIASES.get(lower)
    if alias and hiring_stage_exists(alias):
        return alias
    if hiring_stage_exists(lower):
        return lower
    from backend.app.constants.stages import code_for_label

    mapped = code_for_label(text) or code_for_label(lower)
    if mapped and hiring_stage_exists(mapped):
        return mapped
    return None


def classify_hiring_transition(
    current: str | None,
    target: str,
) -> TransitionKind:
    target_key = normalize_hiring_stage_key(target)
    if not target_key:
        return "jump"
    current_key = normalize_hiring_stage_key(current) if current else None
    if not current_key:
        # Unregistered occupancy may move onto a registered key (escape).
        return "forward"
    if current_key == target_key:
        return "same"
    order = {key: idx for idx, key in enumerate(TRANSITION_ORDER)}
    if current_key not in order or target_key not in order:
        return "jump"
    if order[target_key] > order[current_key]:
        return "forward"
    return "backward"


def assert_hiring_stage_transition(
    current: str | None,
    target: str,
) -> TransitionKind:
    """Production transition-order rule.

    Existence = LI-1. Occupancy = Candidate.stage (caller supplies current).
    Jump = leftover-granted / unregistered target — rejected.
    Forward registered moves stay subject to leftover pipeline guards (HE-3).
    """
    if not str(target or "").strip():
        raise HTTPException(status_code=422, detail="Stage must not be empty")
    kind = classify_hiring_transition(current, target)
    if kind == "jump":
        raise HTTPException(
            status_code=422,
            detail=f"Unknown stage '{target}'",
        )
    return kind


def resolve_hiring_stage_key(raw: str) -> str:
    """Hiring-path existence resolver. Leftover registries do not answer."""
    text = str(raw or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="Stage must not be empty")
    normalized = normalize_hiring_stage_key(text)
    if not normalized:
        raise HTTPException(status_code=422, detail=f"Unknown stage '{text}'")
    return normalized
