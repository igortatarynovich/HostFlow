"""Vacancy Requirements evaluator — fit | missing | not_fit.

Consumes Vacancy Overlay merge (requirements SoT) × canonical fact occupancy.
Never treats transport bags or leftover lead-criteria evaluators as decision authority.

Contract: ``docs/specs/tasks/vacancy-requirements-evaluator.md``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.vacancy_overlay_runtime import (
    merge as merge_overlay,
    resolve_overlay,
)
from backend.app.field_registry.canonical_facts import (
    CITIZENSHIP_QUALIFIED,
    YEARS_CE_QUALIFIED,
    read_citizenship_alpha2,
    read_years_ce,
)

CONTRACT_ID = "vacancy_recruitment_requirements.v1"
STATUS_FIT = "fit"
STATUS_MISSING = "missing"
STATUS_NOT_FIT = "not_fit"

NEXT_FITS = "fits"
NEXT_COLLECT = "collect_fact"
NEXT_REJECT = "reject"

_YEARS_CE = YEARS_CE_QUALIFIED
_CITIZENSHIP = CITIZENSHIP_QUALIFIED

_REQUIREMENT_LABELS: dict[str, str] = {
    YEARS_CE_QUALIFIED: "EU C+E experience (years)",
    CITIZENSHIP_QUALIFIED: "Citizenship",
    "passport": "Passport",
    "driver_license": "Driver license",
    "code95": "Code 95",
    "tacho_card": "Tachograph card",
}


def _requirement_label(*, qualified_code: str | None = None, document_type_code: str | None = None) -> str:
    """Human requirement for UI — never a source field or overlay predicate id."""
    if qualified_code:
        return _REQUIREMENT_LABELS.get(qualified_code, qualified_code.rsplit(".", 1)[-1].replace("_", " "))
    if document_type_code:
        return _REQUIREMENT_LABELS.get(
            document_type_code,
            document_type_code.replace("_", " ").strip().title(),
        )
    return "Required fact"


def evaluate_vacancy_requirements_v1(
    *,
    profile: str | Mapping[str, Any] | None,
    vacancy: Mapping[str, Any] | str | None = None,
    facts_source: Any = None,
    evidence_document_types: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Pure evaluator. Does not persist Candidate, Ready package, or handoff."""
    profile_code = _profile_code(profile) or DRIVER_CE_PROFILE_CODE
    vacancy_payload = vacancy if isinstance(vacancy, Mapping) else {}
    if isinstance(vacancy, str) and vacancy.strip():
        vacancy_payload = {"vacancy_ref": vacancy.strip()}

    overlay = resolve_overlay(profile_code, vacancy_payload)
    if overlay.get("ok") is False:
        return _error_result(overlay)

    refs_pack = overlay.get("base")
    effective = merge_overlay(profile_code, refs_pack, overlay)
    if effective.get("ok") is False:
        return _error_result(effective)

    explanations: list[dict[str, Any]] = []
    explanations.extend(_years_ce_explanations(facts_source, effective))
    explanations.extend(_presence_explanations(facts_source, effective))
    explanations.extend(
        _document_explanations(evidence_document_types or (), effective)
    )

    status = _aggregate_status(explanations)
    return {
        "ok": True,
        "contract_id": CONTRACT_ID,
        "profile_code": profile_code,
        "status": status,
        "explanation": explanations,
        "next_action": _next_action(status, explanations),
        "overlay": {
            "contract_id": overlay.get("contract_id"),
            "vacancy_ref": overlay.get("vacancy_ref"),
            "years_ce_min": effective.get("years_ce_min"),
            "document_types": list(effective.get("document_types") or []),
        },
    }


def contract_metadata() -> dict[str, str]:
    return {
        "contract_id": CONTRACT_ID,
        "proof_profile": DRIVER_CE_PROFILE_CODE,
        "producer": "backend.app.reference.vacancy_requirements",
    }


def _error_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "contract_id": CONTRACT_ID,
        "status": STATUS_MISSING,
        "explanation": [
            {
                "kind": "error",
                "code": str(payload.get("error") or "overlay_error"),
                "outcome": STATUS_MISSING,
                "message": str(payload.get("error") or "overlay_error"),
            }
        ],
        "next_action": {
            "code": NEXT_COLLECT,
            "fact_code": "vacancy_requirements",
            "message": "Resolve vacancy profile / overlay before evaluating fit.",
        },
        "error": payload.get("error"),
    }


def _profile_code(profile: str | Mapping[str, Any] | None) -> str:
    if isinstance(profile, str):
        return profile.strip()
    if isinstance(profile, Mapping):
        for key in ("profile_code", "code", "entity_profile_code"):
            value = str(profile.get(key) or "").strip()
            if value:
                return value
    return ""


def _years_ce_explanations(
    facts_source: Any, effective: Mapping[str, Any]
) -> list[dict[str, Any]]:
    years_min = effective.get("years_ce_min")
    if years_min is None:
        return []
    try:
        minimum = float(years_min)
    except (TypeError, ValueError):
        return []

    raw = read_years_ce(facts_source)
    if raw in (None, ""):
        label = _requirement_label(qualified_code=_YEARS_CE)
        return [
            {
                "kind": "value",
                "code": "years_ce.missing",
                "outcome": STATUS_MISSING,
                "qualified_code": _YEARS_CE,
                "requirement": label,
                "message": f"{label} is required (minimum {minimum:g}) and is not filled yet.",
                "minimum": minimum,
            }
        ]
    try:
        value = float(raw)
    except (TypeError, ValueError):
        label = _requirement_label(qualified_code=_YEARS_CE)
        return [
            {
                "kind": "value",
                "code": "years_ce.unreadable",
                "outcome": STATUS_MISSING,
                "qualified_code": _YEARS_CE,
                "requirement": label,
                "message": f"{label} is present but not a valid number.",
                "minimum": minimum,
            }
        ]
    if value < minimum:
        label = _requirement_label(qualified_code=_YEARS_CE)
        return [
            {
                "kind": "value",
                "code": "years_ce.below_min",
                "outcome": STATUS_NOT_FIT,
                "qualified_code": _YEARS_CE,
                "requirement": label,
                "message": f"{label}: {value:g} is below the vacancy minimum {minimum:g}.",
                "minimum": minimum,
                "actual": value,
            }
        ]
    label = _requirement_label(qualified_code=_YEARS_CE)
    return [
        {
            "kind": "value",
            "code": "years_ce.ok",
            "outcome": STATUS_FIT,
            "qualified_code": _YEARS_CE,
            "requirement": label,
            "message": f"{label}: {value:g} meets minimum {minimum:g}.",
            "minimum": minimum,
            "actual": value,
        }
    ]


def _presence_explanations(
    facts_source: Any, effective: Mapping[str, Any]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in effective.get("presence_required") or []:
        if not isinstance(row, Mapping):
            continue
        qualified = str(row.get("qualified_code") or "").strip()
        if not qualified:
            continue
        value = _read_qualified(facts_source, qualified)
        label = _requirement_label(qualified_code=qualified)
        if value in (None, ""):
            out.append(
                {
                    "kind": "presence",
                    "code": f"presence.missing.{qualified}",
                    "outcome": STATUS_MISSING,
                    "qualified_code": qualified,
                    "requirement": label,
                    "message": f"{label} is required and is not filled yet.",
                }
            )
        else:
            out.append(
                {
                    "kind": "presence",
                    "code": f"presence.ok.{qualified}",
                    "outcome": STATUS_FIT,
                    "qualified_code": qualified,
                    "requirement": label,
                    "message": f"{label} is filled.",
                }
            )
    return out


def _document_explanations(
    evidence_types: Sequence[str], effective: Mapping[str, Any]
) -> list[dict[str, Any]]:
    present = {
        str(code).strip().lower()
        for code in evidence_types
        if str(code).strip()
    }
    out: list[dict[str, Any]] = []
    for doc in effective.get("document_types") or []:
        code = str(doc).strip().lower()
        if not code:
            continue
        label = _requirement_label(document_type_code=code)
        if code in present:
            out.append(
                {
                    "kind": "document",
                    "code": f"document.{code}.ok",
                    "outcome": STATUS_FIT,
                    "document_type_code": code,
                    "requirement": label,
                    "message": f"{label} evidence is present.",
                }
            )
        else:
            out.append(
                {
                    "kind": "document",
                    "code": f"document.{code}.missing",
                    "outcome": STATUS_MISSING,
                    "document_type_code": code,
                    "requirement": label,
                    "message": f"{label} evidence is still missing.",
                }
            )
    return out


def _read_qualified(facts_source: Any, qualified: str) -> Any:
    if qualified == _YEARS_CE:
        return read_years_ce(facts_source)
    if qualified == _CITIZENSHIP:
        return read_citizenship_alpha2(facts_source) or None
    if isinstance(facts_source, Mapping):
        if qualified in facts_source:
            return facts_source.get(qualified)
        identity = facts_source.get("identity_facts")
        if isinstance(identity, Mapping) and qualified.endswith(".citizenship"):
            return identity.get("citizenship")
    return None


def _aggregate_status(explanations: Sequence[Mapping[str, Any]]) -> str:
    outcomes = [str(row.get("outcome") or "") for row in explanations]
    if STATUS_NOT_FIT in outcomes:
        return STATUS_NOT_FIT
    if STATUS_MISSING in outcomes:
        return STATUS_MISSING
    return STATUS_FIT


def _next_action(
    status: str, explanations: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if status == STATUS_FIT:
        return {
            "code": NEXT_FITS,
            "message": "Подходит — create/find Candidate (human boundary).",
        }
    if status == STATUS_NOT_FIT:
        first = next(
            (row for row in explanations if row.get("outcome") == STATUS_NOT_FIT),
            None,
        )
        return {
            "code": NEXT_REJECT,
            "message": "Не подходит — close this Application.",
            "reason_code": str((first or {}).get("code") or "not_fit"),
        }
    first_missing = next(
        (row for row in explanations if row.get("outcome") == STATUS_MISSING),
        None,
    )
    fact_code = None
    requirement = None
    if isinstance(first_missing, Mapping):
        fact_code = first_missing.get("qualified_code") or first_missing.get(
            "document_type_code"
        )
        requirement = first_missing.get("requirement")
        if not requirement and fact_code:
            requirement = _requirement_label(
                qualified_code=str(fact_code)
                if "." in str(fact_code)
                else None,
                document_type_code=None
                if "." in str(fact_code)
                else str(fact_code),
            )
    return {
        "code": NEXT_COLLECT,
        "fact_code": str(fact_code or "required_fact"),
        "requirement": str(requirement or "Required fact"),
        "message": str(
            (first_missing or {}).get("message")
            or f"Collect: {requirement or 'required fact'}."
        ),
    }


__all__ = [
    "CONTRACT_ID",
    "STATUS_FIT",
    "STATUS_MISSING",
    "STATUS_NOT_FIT",
    "NEXT_FITS",
    "NEXT_COLLECT",
    "NEXT_REJECT",
    "evaluate_vacancy_requirements_v1",
    "contract_metadata",
]
