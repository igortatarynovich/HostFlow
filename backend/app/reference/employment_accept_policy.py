"""Employment accept policy — frozen contract (ESO-1).

Policy id: ``employment_accept_policy.v1``.

Employment evaluates a validated ``ready_for_employment.v1`` package and
decides auto-accept vs concrete blockers. Must reuse package facts (gate 2).
Must not be invoked by Recruitment Transfer as its completion.

Not ESO-2 employability SoT. Not formalize depth. Not Started.
"""

from __future__ import annotations

from typing import Any, Final, Mapping

from backend.app.reference.ready_for_employment import (
    ACCEPTANCE_GATE_IDS,
    CONTRACT_ID as RFE_CONTRACT_ID,
    FORBIDDEN_TOP_LEVEL_KEYS as RFE_FORBIDDEN_TOP_LEVEL_KEYS,
    TRANSFER_OPERATOR_ACTION,
    validate_ready_for_employment_package_v1,
)

POLICY_ID: Final[str] = "employment_accept_policy.v1"

OPERATOR_QUESTION: Final[str] = (
    "when Employment receives a validated Ready for employment package and a "
    "pending handoff, under what policy may Employment auto-accept and "
    "initialize — reusing package facts — without a ritual Accept screen and "
    "without re-asking Recruitment?"
)

DECISION_AUTO_ACCEPT: Final[str] = "auto_accept"
DECISION_REVIEW_REQUIRED: Final[str] = "review_required"
DECISION_REJECT_INVALID_PACKAGE: Final[str] = "reject_invalid_package"

DECISION_VALUES: Final[tuple[str, ...]] = (
    DECISION_AUTO_ACCEPT,
    DECISION_REVIEW_REQUIRED,
    DECISION_REJECT_INVALID_PACKAGE,
)

# Package-authoritative codes — must not appear in employment_missing
# without a documented conflict_reason (gate 2).
PACKAGE_AUTHORITATIVE_FIELD_CODES: Final[frozenset[str]] = frozenset(
    {
        "person",
        "person_id",
        "candidate_id",
        "citizenship",
        "nationality",
        "first_name",
        "last_name",
        "vacancy_id",
        "employer_id",
        "target_work",
        "recruitment_facts",
        "evidence",
        "fits_decision",
        "application_id",
    }
)

ARCH_REL: Final[str] = "docs/specs/architecture/employment-accept-policy.md"
ESO_BRIEF_REL: Final[str] = "docs/specs/tasks/employment-spine-orchestrator-v1.md"
RFE_ARCH_REL: Final[str] = "docs/specs/architecture/ready-for-employment-contract.md"
EVALUATE_API: Final[str] = "evaluate_employment_accept_policy_v1"
APPLY_API: Final[str] = "apply_employment_accept_policy"

EMPLOYMENT_STARTED_MESSAGE: Final[str] = "Employment started"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm_code(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def assert_employment_missing_reuses_package(
    employment_missing: list[Mapping[str, Any]] | None,
    *,
    package: Mapping[str, Any] | None = None,
) -> list[str]:
    """Return violation codes when gate 2 is broken.

    A missing row whose field_code is package-authoritative must carry a
    non-empty ``conflict_reason``. Keys already present under package
    ``recruitment_facts`` / ``evidence`` are also authoritative.
    """
    violations: list[str] = []
    authoritative = set(PACKAGE_AUTHORITATIVE_FIELD_CODES)
    if isinstance(package, Mapping):
        facts = package.get("recruitment_facts")
        if isinstance(facts, Mapping):
            authoritative.update(_norm_code(k) for k in facts.keys())
        evidence = package.get("evidence")
        if isinstance(evidence, Mapping):
            authoritative.update(_norm_code(k) for k in evidence.keys())

    for row in employment_missing or []:
        if not isinstance(row, Mapping):
            continue
        code = _norm_code(row.get("field_code") or row.get("code"))
        if not code:
            continue
        if code in authoritative:
            conflict = _text(row.get("conflict_reason"))
            if not conflict:
                violations.append(code)
    return violations


def evaluate_employment_accept_policy_v1(
    *,
    package: Mapping[str, Any] | None,
    handoff_status: str | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
    destination: str | None = None,
    handoff_enabled: bool = True,
) -> dict[str, Any]:
    """Pure policy evaluation. Does not persist. Does not call accept_handoff.

    Returns a decision object with ``policy_id``, ``decision``, blockers, and
    gate metadata.
    """
    package_errors = validate_ready_for_employment_package_v1(package)
    missing = list(employment_missing or [])
    reuse_violations = assert_employment_missing_reuses_package(missing, package=package)

    status = _text(handoff_status).lower()
    dest = _text(destination).lower() or "internal_hr"

    blockers: list[dict[str, str]] = []
    if package_errors:
        for err in package_errors:
            blockers.append({"code": "invalid_package", "message": err})
    if status and status != "pending_review":
        blockers.append(
            {
                "code": "handoff_not_pending",
                "message": f"Handoff status is {status!r}; accept requires pending_review",
            }
        )
    if not handoff_enabled:
        blockers.append(
            {
                "code": "handoff_disabled",
                "message": "Handoff is not enabled for this client link",
            }
        )
    if dest == "internal_hr" and handoff_enabled is False:
        blockers.append(
            {
                "code": "internal_hr_disabled",
                "message": "Internal HR handoff is not enabled",
            }
        )
    for row in missing:
        if isinstance(row, Mapping):
            blockers.append(
                {
                    "code": _norm_code(row.get("field_code") or row.get("code")) or "employment_missing",
                    "message": _text(row.get("label") or row.get("message")) or "Employment missing",
                }
            )
    for code in reuse_violations:
        blockers.append(
            {
                "code": "package_fact_reask",
                "message": (
                    f"employment_missing must not re-ask package fact {code!r} "
                    "without conflict_reason"
                ),
            }
        )

    if package_errors:
        decision = DECISION_REJECT_INVALID_PACKAGE
    elif blockers or reuse_violations:
        decision = DECISION_REVIEW_REQUIRED
    else:
        decision = DECISION_AUTO_ACCEPT

    return {
        "policy_id": POLICY_ID,
        "decision": decision,
        "package_contract_id": RFE_CONTRACT_ID,
        "package_valid": not package_errors,
        "package_errors": package_errors,
        "employment_missing": missing,
        "reuse_violations": reuse_violations,
        "blockers": blockers,
        "ritual_accept_forbidden": decision == DECISION_AUTO_ACCEPT,
        "acceptance_gate_ids": list(ACCEPTANCE_GATE_IDS),
        "transfer_operator_action": TRANSFER_OPERATOR_ACTION,
        "rfe_forbidden_top_level_keys": sorted(RFE_FORBIDDEN_TOP_LEVEL_KEYS),
    }


__all__ = [
    "POLICY_ID",
    "OPERATOR_QUESTION",
    "DECISION_AUTO_ACCEPT",
    "DECISION_REVIEW_REQUIRED",
    "DECISION_REJECT_INVALID_PACKAGE",
    "PACKAGE_AUTHORITATIVE_FIELD_CODES",
    "ARCH_REL",
    "ESO_BRIEF_REL",
    "RFE_ARCH_REL",
    "EVALUATE_API",
    "APPLY_API",
    "EMPLOYMENT_STARTED_MESSAGE",
    "assert_employment_missing_reuses_package",
    "evaluate_employment_accept_policy_v1",
]
