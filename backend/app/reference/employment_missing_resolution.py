"""Employment missing resolution — frozen contract (ESO-3).

Policy id: ``employment_missing_resolution.v1``.

Turns an early-employability result into a minimal executable path:
active blocker/requirement → supply fact/evidence/action → re-evaluate
employability → ready_to_formalize or updated active items.

Does not create Employee. Does not emit a universal legal checklist.
Eligibility SoT remains ``early_employability.v1`` (ESO-2).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Final, Mapping

from backend.app.reference.early_employability import (
    DECISION_BLOCKED,
    DECISION_EMPLOYABLE,
    DECISION_INSUFFICIENT_FACTS,
    POLICY_ID as EMPLOYABILITY_POLICY_ID,
    evaluate_early_employability_v1,
)
from backend.app.reference.employment_accept_policy import (
    PACKAGE_AUTHORITATIVE_FIELD_CODES,
    assert_employment_missing_reuses_package,
)
from backend.app.reference.ready_for_employment import ACCEPTANCE_GATE_IDS

POLICY_ID: Final[str] = "employment_missing_resolution.v1"

OPERATOR_QUESTION: Final[str] = (
    "given the latest early-employability decision, what is the minimal fact, "
    "evidence, or action the operator must supply next, and after supplying it, "
    "what is the updated employability outcome — without showing a full legal "
    "checklist and without creating an Employee?"
)

RESOLUTION_READY: Final[str] = "ready_to_formalize"
RESOLUTION_AWAITING: Final[str] = "awaiting_input"
RESOLUTION_STILL_BLOCKED: Final[str] = "still_blocked"
RESOLUTION_REJECTED_PATCH: Final[str] = "rejected_patch"

RESOLUTION_DECISIONS: Final[tuple[str, ...]] = (
    RESOLUTION_READY,
    RESOLUTION_AWAITING,
    RESOLUTION_STILL_BLOCKED,
    RESOLUTION_REJECTED_PATCH,
)

# Codes that must never appear as a dumped universal checklist in active_items
# unless they are on the current employability result.
FORBIDDEN_UNIVERSAL_CHECKLIST_CODES: Final[frozenset[str]] = frozenset(
    {
        "full_legalization_checklist",
        "universal_legal_checklist",
        "all_legalization_documents",
        "complete_hr_onboarding_pack",
    }
)

ARCH_REL: Final[str] = "docs/specs/architecture/employment-missing-resolution.md"
ESO_BRIEF_REL: Final[str] = "docs/specs/tasks/employment-spine-orchestrator-v1.md"
EMPLOYABILITY_ARCH_REL: Final[str] = "docs/specs/architecture/early-employability.md"
PLAN_API: Final[str] = "plan_employment_resolution_v1"
APPLY_API: Final[str] = "apply_employment_resolution_v1"
RUNTIME_API: Final[str] = "resolve_employment_missing_for_handoff"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm_code(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def plan_employment_resolution_v1(
    employability: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Project ESO-2 result into minimal active items (no universal checklist)."""
    emp = _record(employability)
    decision = _text(emp.get("decision"))
    blockers = [dict(b) for b in (emp.get("blockers") or []) if isinstance(b, Mapping)]
    requirements = [dict(r) for r in (emp.get("requirements") or []) if isinstance(r, Mapping)]
    next_step = emp.get("next_step") if isinstance(emp.get("next_step"), Mapping) else None

    active: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(item: Mapping[str, Any], *, kind: str) -> None:
        code = _norm_code(item.get("code") or item.get("field_code"))
        if not code or code in seen:
            return
        if code in FORBIDDEN_UNIVERSAL_CHECKLIST_CODES:
            return
        seen.add(code)
        active.append(
            {
                "code": code,
                "kind": kind,
                "message": _text(item.get("message") or item.get("label") or item.get("code")),
            }
        )

    for row in blockers:
        _add(row, kind="blocker")
    for row in requirements:
        _add(row, kind="requirement")

    primary: dict[str, Any] | None = None
    if next_step:
        primary = {
            "code": _norm_code(next_step.get("code")) or "next_step",
            "kind": "next_step",
            "message": _text(next_step.get("label") or next_step.get("code")),
        }
        if primary["code"] not in seen and primary["code"] not in FORBIDDEN_UNIVERSAL_CHECKLIST_CODES:
            # Primary may duplicate a requirement code — still surface once as primary.
            pass

    if decision == DECISION_EMPLOYABLE:
        resolution = RESOLUTION_READY
        active = []
        primary = {
            "code": "proceed_to_formalize",
            "kind": "next_step",
            "message": _text((next_step or {}).get("label"))
            or "Proceed to Formalize (Employee still downstream)",
        }
    elif decision == DECISION_INSUFFICIENT_FACTS:
        resolution = RESOLUTION_AWAITING
    elif decision == DECISION_BLOCKED:
        resolution = RESOLUTION_STILL_BLOCKED
    else:
        resolution = RESOLUTION_STILL_BLOCKED

    return {
        "policy_id": POLICY_ID,
        "resolution_decision": resolution,
        "active_items": active,
        "primary_item": primary,
        "universal_checklist_forbidden": True,
        "employee_created": False,
        "employability_policy_id": EMPLOYABILITY_POLICY_ID,
        "employability_decision": decision or None,
        "acceptance_gate_ids": list(ACCEPTANCE_GATE_IDS),
    }


def merge_resolution_patch_into_package(
    package: Mapping[str, Any] | None,
    patch: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a deep-copied package with minimal facts/evidence merged."""
    base = deepcopy(dict(package or {}))
    p = _record(patch)
    facts = _record(p.get("facts"))
    evidence_patch = _record(p.get("evidence"))

    if facts:
        person = _record(base.get("person"))
        identity = _record(person.get("identity_facts"))
        for key, value in facts.items():
            identity[key] = value
        person["identity_facts"] = identity
        # Keep top-level mirrors for readers that look there.
        for key in ("citizenship", "nationality"):
            if key in facts:
                person[key] = facts[key]
        base["person"] = person

    if evidence_patch:
        evidence = _record(base.get("evidence"))
        evidence.update(evidence_patch)
        base["evidence"] = evidence

    return base


def _patch_is_empty(patch: Mapping[str, Any] | None) -> bool:
    p = _record(patch)
    facts = _record(p.get("facts"))
    evidence = _record(p.get("evidence"))
    actions = p.get("actions")
    has_actions = isinstance(actions, list) and any(True for _ in actions)
    return not facts and not evidence and not has_actions


def apply_employment_resolution_v1(
    *,
    package: Mapping[str, Any] | None,
    handoff_status: str | None,
    employment_context: Mapping[str, Any] | None = None,
    resolution_patch: Mapping[str, Any] | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
    require_patch_when_not_ready: bool = False,
) -> dict[str, Any]:
    """Merge patch (optional) → re-evaluate employability → plan active items.

    When ``require_patch_when_not_ready`` and current state is not employable and
    patch is empty, returns ``rejected_patch`` without pretending progress.
    """
    missing = list(employment_missing or [])
    # Treat resolution fact keys that collide with package-authoritative codes as
    # employment_missing-style rows when supplied without conflict_reason via missing list.
    reuse_violations = assert_employment_missing_reuses_package(missing, package=package)

    # Baseline evaluate (pre-patch) to know if input is required.
    baseline = evaluate_early_employability_v1(
        package=package,
        handoff_status=handoff_status,
        employment_context=employment_context,
        employment_missing=missing,
    )
    baseline_plan = plan_employment_resolution_v1(baseline)

    patch = _record(resolution_patch)
    empty_patch = _patch_is_empty(patch)

    if reuse_violations:
        return {
            "policy_id": POLICY_ID,
            "resolution_decision": RESOLUTION_REJECTED_PATCH,
            "active_items": baseline_plan["active_items"],
            "primary_item": baseline_plan["primary_item"],
            "universal_checklist_forbidden": True,
            "employee_created": False,
            "package_merged": False,
            "reuse_violations": reuse_violations,
            "employability": baseline,
            "plan": baseline_plan,
            "rejection_reason": "package_fact_reask_without_conflict_reason",
            "acceptance_gate_ids": list(ACCEPTANCE_GATE_IDS),
            "package_authoritative_field_codes": sorted(PACKAGE_AUTHORITATIVE_FIELD_CODES),
        }

    if (
        require_patch_when_not_ready
        and baseline.get("decision") != DECISION_EMPLOYABLE
        and empty_patch
    ):
        return {
            "policy_id": POLICY_ID,
            "resolution_decision": RESOLUTION_REJECTED_PATCH,
            "active_items": baseline_plan["active_items"],
            "primary_item": baseline_plan["primary_item"],
            "universal_checklist_forbidden": True,
            "employee_created": False,
            "package_merged": False,
            "reuse_violations": [],
            "employability": baseline,
            "plan": baseline_plan,
            "rejection_reason": "patch_required_for_current_blocker",
            "acceptance_gate_ids": list(ACCEPTANCE_GATE_IDS),
            "package_authoritative_field_codes": sorted(PACKAGE_AUTHORITATIVE_FIELD_CODES),
        }

    merged = (
        merge_resolution_patch_into_package(package, patch)
        if not empty_patch
        else deepcopy(dict(package or {}))
    )

    # Auto re-evaluate — happy path has no separate ritual recheck step.
    employability = evaluate_early_employability_v1(
        package=merged,
        handoff_status=handoff_status,
        employment_context=employment_context,
        employment_missing=missing,
    )
    plan = plan_employment_resolution_v1(employability)

    return {
        "policy_id": POLICY_ID,
        "resolution_decision": plan["resolution_decision"],
        "active_items": plan["active_items"],
        "primary_item": plan["primary_item"],
        "universal_checklist_forbidden": True,
        "employee_created": False,
        "package_merged": not empty_patch,
        "reuse_violations": [],
        "employability": employability,
        "plan": plan,
        "rejection_reason": None,
        "acceptance_gate_ids": list(ACCEPTANCE_GATE_IDS),
        "package_authoritative_field_codes": sorted(PACKAGE_AUTHORITATIVE_FIELD_CODES),
    }


__all__ = [
    "POLICY_ID",
    "OPERATOR_QUESTION",
    "RESOLUTION_READY",
    "RESOLUTION_AWAITING",
    "RESOLUTION_STILL_BLOCKED",
    "RESOLUTION_REJECTED_PATCH",
    "RESOLUTION_DECISIONS",
    "FORBIDDEN_UNIVERSAL_CHECKLIST_CODES",
    "ARCH_REL",
    "ESO_BRIEF_REL",
    "EMPLOYABILITY_ARCH_REL",
    "PLAN_API",
    "APPLY_API",
    "RUNTIME_API",
    "plan_employment_resolution_v1",
    "merge_resolution_patch_into_package",
    "apply_employment_resolution_v1",
]
