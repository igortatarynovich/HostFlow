"""Employment formalize — frozen contract (ESO-4).

Policy id: ``employment_formalize.v1``.

After ``ready_to_formalize``, derive context/pathway-required formal actions,
resolve only what is still missing, and emit ``formalization_complete`` with
machine-verifiable ``ready_to_create_employee`` — without creating Employee,
without an HR card, and without a universal checklist.

LLM-OFF for formalize / allow-create decisions.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Final, Mapping

from backend.app.reference.early_employability import (
    DECISION_EMPLOYABLE,
    PATHWAY_PL_EU_EEA,
    PATHWAY_PL_THIRD_COUNTRY,
    evaluate_early_employability_v1,
    evidence_has_work_authorization,
)
from backend.app.reference.employment_accept_policy import (
    PACKAGE_AUTHORITATIVE_FIELD_CODES,
    assert_employment_missing_reuses_package,
)
from backend.app.reference.employment_missing_resolution import (
    FORBIDDEN_UNIVERSAL_CHECKLIST_CODES,
    RESOLUTION_READY,
    apply_employment_resolution_v1,
)
from backend.app.reference.ready_for_employment import ACCEPTANCE_GATE_IDS

POLICY_ID: Final[str] = "employment_formalize.v1"

OPERATOR_QUESTION: Final[str] = (
    "given a handoff that is ready to formalize, plus employment context and "
    "confirmed canonical facts/evidence, which formal actions/documents are "
    "mandatory for this context, and after resolving only what is still missing, "
    "is formalization complete / blocked / missing — and only then may HostFlow "
    "emit machine-verifiable ready_to_create_employee?"
)

DECISION_COMPLETE: Final[str] = "formalization_complete"
DECISION_MISSING: Final[str] = "missing"
DECISION_BLOCKED: Final[str] = "blocked"
DECISION_REJECTED_PATCH: Final[str] = "rejected_patch"

DECISION_VALUES: Final[tuple[str, ...]] = (
    DECISION_COMPLETE,
    DECISION_MISSING,
    DECISION_BLOCKED,
    DECISION_REJECTED_PATCH,
)

ACTION_CONTRACT_BASIS: Final[str] = "confirm_employment_contract_basis"
ACTION_IDENTITY_PRESENT: Final[str] = "identity_facts_present"
ACTION_WORK_AUTH: Final[str] = "work_authorization_evidence"

ARCH_REL: Final[str] = "docs/specs/architecture/employment-formalize.md"
ESO_BRIEF_REL: Final[str] = "docs/specs/tasks/employment-spine-orchestrator-v1.md"
RESOLUTION_ARCH_REL: Final[str] = "docs/specs/architecture/employment-missing-resolution.md"
EVALUATE_API: Final[str] = "evaluate_employment_formalize_v1"
APPLY_API: Final[str] = "apply_employment_formalize_v1"
RUNTIME_API: Final[str] = "formalize_employment_for_handoff"

READY_TO_CREATE_EMPLOYEE: Final[str] = "ready_to_create_employee"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm_code(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _confirmed_set(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        raw = value.get("confirmed_actions") or value.get("actions") or []
    else:
        raw = value or []
    out: set[str] = set()
    if isinstance(raw, Mapping):
        for key, flag in raw.items():
            if flag:
                out.add(_norm_code(key))
        return out
    for row in raw:
        if isinstance(row, Mapping):
            code = _norm_code(row.get("code") or row.get("action"))
            if code and row.get("confirmed", True) is not False:
                out.add(code)
        else:
            code = _norm_code(row)
            if code:
                out.add(code)
    return out


def _identity_facts_present(package: Mapping[str, Any] | None) -> bool:
    person = _record((_record(package)).get("person"))
    identity = _record(person.get("identity_facts"))
    citizenship = _text(identity.get("citizenship") or person.get("citizenship"))
    name = _text(identity.get("first_name") or person.get("first_name"))
    return bool(citizenship) and bool(name)


def required_formal_actions_v1(
    *,
    pathway_id: str | None,
    employment_context: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Context/pathway-derived required formal items (thin PL table)."""
    _ = employment_context  # reserved for position refinements (labels only)
    pathway = _norm_code(pathway_id)
    required: list[dict[str, str]] = []

    if pathway == _norm_code(PATHWAY_PL_EU_EEA):
        required.append(
            {
                "code": ACTION_IDENTITY_PRESENT,
                "kind": "reuse_check",
                "message": "Identity facts already on package (citizenship + name)",
            }
        )
        required.append(
            {
                "code": ACTION_CONTRACT_BASIS,
                "kind": "confirmation",
                "message": "Confirm employment contract basis for this PL EU/EEA hire",
            }
        )
    elif pathway == _norm_code(PATHWAY_PL_THIRD_COUNTRY):
        required.append(
            {
                "code": ACTION_WORK_AUTH,
                "kind": "evidence",
                "message": "Work authorization evidence on file for this pathway",
            }
        )
        required.append(
            {
                "code": ACTION_CONTRACT_BASIS,
                "kind": "confirmation",
                "message": "Confirm employment contract basis for this PL third-country hire",
            }
        )
    return required


def _is_action_satisfied(
    code: str,
    *,
    package: Mapping[str, Any] | None,
    confirmed: set[str],
) -> bool:
    c = _norm_code(code)
    if c == ACTION_IDENTITY_PRESENT:
        return _identity_facts_present(package)
    if c == ACTION_WORK_AUTH:
        return evidence_has_work_authorization(package) or c in confirmed
    if c == ACTION_CONTRACT_BASIS:
        return c in confirmed
    return c in confirmed


def evaluate_employment_formalize_v1(
    *,
    package: Mapping[str, Any] | None,
    handoff_status: str | None,
    employment_context: Mapping[str, Any] | None = None,
    confirmed_actions: Mapping[str, Any] | list[Any] | None = None,
    ready_to_formalize: bool | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Pure formalize evaluation. Does not create Employee. LLM-OFF."""
    missing_rows = list(employment_missing or [])
    reuse_violations = assert_employment_missing_reuses_package(missing_rows, package=package)

    # Reuse ESO-3 apply (empty patch) as readiness oracle when not explicitly passed.
    if ready_to_formalize is None:
        resolution = apply_employment_resolution_v1(
            package=package,
            handoff_status=handoff_status,
            employment_context=employment_context,
            resolution_patch={},
            employment_missing=missing_rows,
            require_patch_when_not_ready=False,
        )
        ready = resolution.get("resolution_decision") == RESOLUTION_READY
        employability = _record(resolution.get("employability"))
    else:
        ready = bool(ready_to_formalize)
        employability = evaluate_early_employability_v1(
            package=package,
            handoff_status=handoff_status,
            employment_context=employment_context,
            employment_missing=missing_rows,
        )

    pathway_obj = employability.get("legal_pathway") if isinstance(employability, Mapping) else None
    pathway_id = None
    if isinstance(pathway_obj, Mapping):
        pathway_id = pathway_obj.get("pathway_id")

    confirmed = _confirmed_set(confirmed_actions)
    required = required_formal_actions_v1(
        pathway_id=str(pathway_id) if pathway_id else None,
        employment_context=employment_context,
    )

    blockers: list[dict[str, str]] = []
    if reuse_violations:
        for code in reuse_violations:
            blockers.append(
                {
                    "code": "package_fact_reask",
                    "message": f"must not re-ask package fact {code!r} without conflict_reason",
                }
            )
    if not ready:
        blockers.append(
            {
                "code": "not_ready_to_formalize",
                "message": "Formalize requires ready_to_formalize (ESO-3) / employable package",
            }
        )
    if ready and employability.get("decision") != DECISION_EMPLOYABLE:
        blockers.append(
            {
                "code": "employability_not_employable",
                "message": "Formalize requires employable decision from early_employability.v1",
            }
        )
    if ready and not pathway_id:
        blockers.append(
            {
                "code": "pathway_unresolved",
                "message": "Legal pathway must be uniquely determined before formalize",
            }
        )

    active_missing: list[dict[str, str]] = []
    if ready and pathway_id and not reuse_violations:
        for item in required:
            code = item["code"]
            if _is_action_satisfied(code, package=package, confirmed=confirmed):
                continue
            if code in FORBIDDEN_UNIVERSAL_CHECKLIST_CODES:
                continue
            active_missing.append(dict(item))

    if reuse_violations or (blockers and not ready) or any(
        b.get("code") in {"employability_not_employable", "pathway_unresolved"} for b in blockers
    ):
        decision = DECISION_BLOCKED
        primary = {
            "code": "resolve_preconditions",
            "kind": "blocker",
            "message": "Resolve ready_to_formalize / employability preconditions",
        }
        ready_create = False
    elif active_missing:
        decision = DECISION_MISSING
        primary = {
            "code": active_missing[0]["code"],
            "kind": active_missing[0].get("kind") or "formal_action",
            "message": active_missing[0].get("message") or active_missing[0]["code"],
        }
        ready_create = False
    else:
        decision = DECISION_COMPLETE
        primary = {
            "code": READY_TO_CREATE_EMPLOYEE,
            "kind": "threshold",
            "message": "Formalization complete — Employee creation allowed (not Created)",
        }
        ready_create = True

    return {
        "policy_id": POLICY_ID,
        "decision": decision,
        "required_actions": required,
        "active_missing": active_missing,
        "primary_item": primary,
        "ready_to_formalize": ready,
        "ready_to_create_employee": ready_create,
        "employee_created": False,
        "hr_employee_card": False,
        "universal_checklist_forbidden": True,
        "llm_formalize": False,
        "pathway_id": pathway_id,
        "blockers": blockers,
        "reuse_violations": reuse_violations,
        "confirmed_actions": sorted(confirmed),
        "employability_decision": employability.get("decision"),
        "acceptance_gate_ids": list(ACCEPTANCE_GATE_IDS),
        "package_authoritative_field_codes": sorted(PACKAGE_AUTHORITATIVE_FIELD_CODES),
    }


def apply_employment_formalize_v1(
    *,
    package: Mapping[str, Any] | None,
    handoff_status: str | None,
    employment_context: Mapping[str, Any] | None = None,
    formalize_patch: Mapping[str, Any] | None = None,
    confirmed_actions: Mapping[str, Any] | list[Any] | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
    require_patch_when_missing: bool = False,
) -> dict[str, Any]:
    """Merge formalize confirmations/evidence → re-evaluate formalize decision."""
    patch = _record(formalize_patch)
    evidence_patch = _record(patch.get("evidence"))
    facts_patch = _record(patch.get("facts"))

    confirmed = _confirmed_set(confirmed_actions)
    confirmed |= _confirmed_set(patch)
    for key, value in patch.items():
        if key in {"evidence", "facts", "actions", "confirmed_actions"}:
            continue
        if value:
            confirmed.add(_norm_code(key))

    patch_empty = not evidence_patch and not facts_patch and not (
        confirmed - _confirmed_set(confirmed_actions)
    )

    baseline = evaluate_employment_formalize_v1(
        package=package,
        handoff_status=handoff_status,
        employment_context=employment_context,
        confirmed_actions=sorted(_confirmed_set(confirmed_actions)),
        employment_missing=employment_missing,
    )

    if (
        require_patch_when_missing
        and baseline.get("decision") == DECISION_MISSING
        and patch_empty
    ):
        return {
            **baseline,
            "decision": DECISION_REJECTED_PATCH,
            "ready_to_create_employee": False,
            "employee_created": False,
            "package_merged": False,
            "rejection_reason": "patch_required_for_current_formal_item",
        }

    merged_package = deepcopy(dict(package or {}))
    if facts_patch:
        person = _record(merged_package.get("person"))
        identity = _record(person.get("identity_facts"))
        identity.update(facts_patch)
        person["identity_facts"] = identity
        merged_package["person"] = person
    if evidence_patch:
        evidence = _record(merged_package.get("evidence"))
        evidence.update(evidence_patch)
        merged_package["evidence"] = evidence

    result = evaluate_employment_formalize_v1(
        package=merged_package,
        handoff_status=handoff_status,
        employment_context=employment_context,
        confirmed_actions=sorted(confirmed),
        employment_missing=employment_missing,
    )
    result["package_merged"] = bool(evidence_patch or facts_patch)
    result["rejection_reason"] = None
    return result


__all__ = [
    "POLICY_ID",
    "OPERATOR_QUESTION",
    "DECISION_COMPLETE",
    "DECISION_MISSING",
    "DECISION_BLOCKED",
    "DECISION_REJECTED_PATCH",
    "DECISION_VALUES",
    "ACTION_CONTRACT_BASIS",
    "ACTION_IDENTITY_PRESENT",
    "ACTION_WORK_AUTH",
    "ARCH_REL",
    "ESO_BRIEF_REL",
    "RESOLUTION_ARCH_REL",
    "EVALUATE_API",
    "APPLY_API",
    "RUNTIME_API",
    "READY_TO_CREATE_EMPLOYEE",
    "required_formal_actions_v1",
    "evaluate_employment_formalize_v1",
    "apply_employment_formalize_v1",
]
