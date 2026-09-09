"""Full spine happy path — frozen contract (Full Spine Gate).

Policy id: ``full_spine.v1``.

One inbound package → Accept → Employability → Resolution → Formalize
→ Employee allow → Started. Employee created ≠ Started.
Known facts are not re-asked. Pathway is not an operator dropdown.
LLM-OFF.

This freeze is necessary and not sufficient for named-gate PASS
(operator / Zero-choice witness is required before integration).
"""

from __future__ import annotations

from typing import Any, Final, Mapping

from backend.app.core.audit_events import AuditEventType
from backend.app.reference.early_employability import (
    DECISION_EMPLOYABLE,
    evaluate_early_employability_v1,
)
from backend.app.reference.employment_accept_policy import (
    DECISION_AUTO_ACCEPT,
    PACKAGE_AUTHORITATIVE_FIELD_CODES,
    assert_employment_missing_reuses_package,
    evaluate_employment_accept_policy_v1,
)
from backend.app.reference.employment_formalize import (
    ACTION_CONTRACT_BASIS,
    DECISION_COMPLETE as FORMALIZE_COMPLETE,
    apply_employment_formalize_v1,
)
from backend.app.reference.employment_missing_resolution import (
    RESOLUTION_READY,
    apply_employment_resolution_v1,
)
from backend.app.reference.employment_started import (
    AUDIT_EVENT_PHYSICAL_START,
    DECISION_ALREADY_STARTED,
    DECISION_STARTED,
    apply_employment_started_v1,
)
from backend.app.reference.ready_for_employment import (
    CONTRACT_ID as RFE_CONTRACT_ID,
    validate_ready_for_employment_package_v1,
)

POLICY_ID: Final[str] = "full_spine.v1"

OPERATOR_QUESTION: Final[str] = (
    "can an untrained operator take one incoming lead to Started on a single "
    "continuous person, without servicing module boundaries, without re-entering "
    "known facts, and without choosing stage / status / pathway — seeing only "
    "the current blocker or one next action?"
)

ARCH_REL: Final[str] = "docs/specs/gates/full-spine-gate.md"
RSO_BRIEF_REL: Final[str] = "docs/specs/tasks/recruitment-spine-orchestrator-v1.md"
ESO_BRIEF_REL: Final[str] = "docs/specs/tasks/employment-spine-orchestrator-v1.md"
WALK_API: Final[str] = "walk_full_spine_happy_path_v1"

SPINE_STEPS: Final[tuple[str, ...]] = (
    "source",
    "recruitment_fits",
    "handoff_package",
    "employment_accept",
    "employability",
    "missing_resolution",
    "formalize",
    "employee",
    "started",
)

FORBIDDEN_HAPPY_PATH_CONTROLS: Final[frozenset[str]] = frozenset(
    {
        "stage_dropdown",
        "status_dropdown",
        "pathway_dropdown",
        "create_candidate_ritual",
        "vacancy_picker_when_known",
        "employer_picker_when_known",
        "ritual_accept",
        "universal_legal_checklist",
    }
)

OPERATOR_VERBS: Final[tuple[str, ...]] = (
    "Позвонить",
    "Подходит",
    "Передать на трудоустройство",
    "Оформить",
    "Подтвердить выход",
)


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def walk_full_spine_happy_path_v1(
    *,
    package: Mapping[str, Any] | None,
    employment_context: Mapping[str, Any] | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Deterministic contract walk. Does not hit IO. LLM-OFF."""
    ctx = dict(employment_context or {})
    if not ctx.get("employment_country"):
        target = _record((_record(package)).get("target_work"))
        country = str(target.get("employment_country") or target.get("country") or "PL").strip()
        if country:
            ctx["employment_country"] = country

    package_errors = validate_ready_for_employment_package_v1(package)
    reuse = assert_employment_missing_reuses_package(employment_missing, package=package)

    accept = evaluate_employment_accept_policy_v1(
        package=package,
        handoff_status="pending_review",
        employment_missing=employment_missing,
        destination="internal_hr",
        handoff_enabled=True,
    )
    employability = evaluate_early_employability_v1(
        package=package,
        handoff_status="accepted",
        employment_context=ctx,
        employment_missing=employment_missing,
    )
    resolution = apply_employment_resolution_v1(
        package=package,
        handoff_status="accepted",
        employment_context=ctx,
        resolution_patch={},
        employment_missing=employment_missing,
        require_patch_when_not_ready=False,
    )
    formalize = apply_employment_formalize_v1(
        package=package,
        handoff_status="accepted",
        employment_context=ctx,
        formalize_patch={"confirmed_actions": [ACTION_CONTRACT_BASIS]},
        employment_missing=employment_missing,
    )
    started = apply_employment_started_v1(
        package=package,
        handoff_status="accepted",
        employment_context=ctx,
        employee_id="spine-employee-1",
        ready_to_create_employee=bool(formalize.get("ready_to_create_employee")),
        start_confirmation={"confirmed": True},
        employment_missing=employment_missing,
    )
    replay = apply_employment_started_v1(
        package=package,
        handoff_status="accepted",
        employment_context=ctx,
        employee_id="spine-employee-1",
        ready_to_create_employee=True,
        prior_start={
            "start_date": started.get("start_date"),
            "employment_context": started.get("employment_context"),
            "event_id": AUDIT_EVENT_PHYSICAL_START,
        },
        start_confirmation={"confirmed": True},
        employment_missing=employment_missing,
    )

    pathway = employability.get("legal_pathway") if isinstance(employability.get("legal_pathway"), Mapping) else {}
    pathway_unique = bool(
        isinstance(pathway, Mapping)
        and pathway.get("uniquely_determined")
        and pathway.get("pathway_id")
        and employability.get("pathway_selection_required") is False
    )

    closed = (
        not package_errors
        and not reuse
        and accept.get("decision") == DECISION_AUTO_ACCEPT
        and employability.get("decision") == DECISION_EMPLOYABLE
        and pathway_unique
        and resolution.get("resolution_decision") == RESOLUTION_READY
        and formalize.get("decision") == FORMALIZE_COMPLETE
        and formalize.get("ready_to_create_employee") is True
        and formalize.get("employee_created") is False
        and started.get("decision") == DECISION_STARTED
        and started.get("started") is True
        and started.get("employee_created_implies_started") is False
        and started.get("formalization_complete_implies_started") is False
        and replay.get("decision") == DECISION_ALREADY_STARTED
        and replay.get("start_event_emitted") is False
        and replay.get("idempotent_replay") is True
    )

    recruitment_completed = (
        AuditEventType.recruitment_completed.value
        if hasattr(AuditEventType, "recruitment_completed")
        else "recruitment_completed"
    )

    return {
        "policy_id": POLICY_ID,
        "package_contract_id": RFE_CONTRACT_ID,
        "spine_steps": list(SPINE_STEPS),
        "package_valid": not package_errors,
        "package_errors": package_errors,
        "reuse_violations": reuse,
        "accept": accept,
        "employability": employability,
        "resolution": resolution,
        "formalize": formalize,
        "started": started,
        "started_replay": replay,
        "pathway_id": pathway.get("pathway_id") if isinstance(pathway, Mapping) else None,
        "pathway_dropdown_required": False,
        "one_next_action": True,
        "employee_created_implies_started": False,
        "audit_recruitment_completed": recruitment_completed,
        "audit_employment_case_started": AuditEventType.employment_started.value,
        "audit_physical_start": AUDIT_EVENT_PHYSICAL_START,
        "audits_distinct": AuditEventType.employment_started.value != AUDIT_EVENT_PHYSICAL_START,
        "forbidden_happy_path_controls": sorted(FORBIDDEN_HAPPY_PATH_CONTROLS),
        "operator_verbs": list(OPERATOR_VERBS),
        "package_authoritative_field_codes": sorted(PACKAGE_AUTHORITATIVE_FIELD_CODES),
        "spine_closed": closed,
        "happy_path": closed,
        "operator_pass_required": True,
        "operator_pass_recorded": False,
        "llm_spine": False,
    }


__all__ = [
    "POLICY_ID",
    "OPERATOR_QUESTION",
    "ARCH_REL",
    "RSO_BRIEF_REL",
    "ESO_BRIEF_REL",
    "WALK_API",
    "SPINE_STEPS",
    "FORBIDDEN_HAPPY_PATH_CONTROLS",
    "OPERATOR_VERBS",
    "walk_full_spine_happy_path_v1",
]
