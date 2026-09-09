"""Ready for employment — frozen handoff package contract (RSO-1).

Contract id: ``ready_for_employment.v1``.

Recruitment's terminal result is a valid package. Employment reuses package
facts; the operator does not service the module boundary.

Not Employment accept policy (ESO-1). Not employability SoT. Not Employee
create. Not legacy ``build_handoff_snapshot_payload_v1`` (cutover later).
Not Mapping. Not Hiring E2E schedule.
"""

from __future__ import annotations

from typing import Any, Final, Mapping

CONTRACT_ID: Final[str] = "ready_for_employment.v1"

OPERATOR_QUESTION: Final[str] = (
    "when Recruitment decides a person fits this vacancy/employer context, "
    "what immutable package must be emitted so Employment can continue "
    "without re-running Recruitment — and without the operator servicing "
    "the module boundary?"
)

REQUIRED_TOP_LEVEL_KEYS: Final[tuple[str, ...]] = (
    "contract_id",
    "tenant_id",
    "person",
    "target_work",
    "recruitment_facts",
    "evidence",
    "fits_decision",
    "context_refs",
)

FORBIDDEN_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "employee_id",
        "employment_missing",
        "legalization_pathway",
        "zus_journey",
        "create_employee",
        "accept_handoff",
    }
)

# Three acceptance gates — bind every subsequent RSO/ESO change.
ACCEPTANCE_GATE_IDS: Final[tuple[str, ...]] = (
    "rso_terminal_is_package",
    "eso_reuses_package_no_reask",
    "operator_does_not_service_boundary",
)

TRANSFER_OPERATOR_ACTION: Final[str] = "Передать на трудоустройство"

ARCH_REL: Final[str] = "docs/specs/architecture/ready-for-employment-contract.md"
RSO_BRIEF_REL: Final[str] = "docs/specs/tasks/recruitment-spine-orchestrator-v1.md"
ESO_BRIEF_REL: Final[str] = "docs/specs/tasks/employment-spine-orchestrator-v1.md"
VALIDATE_API: Final[str] = "validate_ready_for_employment_package_v1"


def validate_ready_for_employment_package_v1(
    package: Mapping[str, Any] | None,
) -> list[str]:
    """Return human-readable validation errors; empty list means valid.

    Does not persist. Does not create Employee. Does not accept handoff.
    """
    errors: list[str] = []
    if not isinstance(package, Mapping):
        return ["package must be a mapping"]

    for key in FORBIDDEN_TOP_LEVEL_KEYS:
        if key in package:
            errors.append(f"forbidden top-level key: {key}")

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in package:
            errors.append(f"missing required key: {key}")

    if errors and "contract_id" not in package:
        return errors

    if package.get("contract_id") != CONTRACT_ID:
        errors.append(f"contract_id must be {CONTRACT_ID!r}")

    tenant_id = package.get("tenant_id")
    if tenant_id is None or not str(tenant_id).strip():
        errors.append("tenant_id must be a non-empty string")

    person = package.get("person")
    if not isinstance(person, Mapping):
        errors.append("person must be an object")
    else:
        person_id = person.get("person_id") or person.get("candidate_id")
        if person_id is None or not str(person_id).strip():
            errors.append("person.person_id (or candidate_id) is required")
        identity = person.get("identity_facts")
        if identity is not None and not isinstance(identity, Mapping):
            errors.append("person.identity_facts must be an object when present")

    target = package.get("target_work")
    if not isinstance(target, Mapping):
        errors.append("target_work must be an object")
    else:
        vac = target.get("vacancy_id")
        emp = target.get("employer_id")
        vac_ok = vac is not None and str(vac).strip()
        emp_ok = emp is not None and str(emp).strip()
        if not vac_ok and not emp_ok:
            errors.append("target_work requires vacancy_id and/or employer_id")

    for block_name in ("recruitment_facts", "evidence"):
        block = package.get(block_name)
        if block_name in package and not isinstance(block, Mapping):
            errors.append(f"{block_name} must be an object")

    fits = package.get("fits_decision")
    if not isinstance(fits, Mapping):
        errors.append("fits_decision must be an object")
    else:
        if str(fits.get("decision") or "").strip().lower() != "fits":
            errors.append("fits_decision.decision must be 'fits'")
        if fits.get("decided_at") is None or not str(fits.get("decided_at")).strip():
            errors.append("fits_decision.decided_at is required")
        if fits.get("actor_id") is None or not str(fits.get("actor_id")).strip():
            errors.append("fits_decision.actor_id is required")

    refs = package.get("context_refs")
    if not isinstance(refs, Mapping):
        errors.append("context_refs must be an object")
    else:
        app_id = refs.get("application_id")
        if app_id is None or not str(app_id).strip():
            errors.append("context_refs.application_id is required")

    return errors


def is_valid_ready_for_employment_package_v1(package: Mapping[str, Any] | None) -> bool:
    return not validate_ready_for_employment_package_v1(package)
