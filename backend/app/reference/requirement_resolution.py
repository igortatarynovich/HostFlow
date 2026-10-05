"""Recruitment runtime of ``requirement_resolution.v1``.

One recruitment requirement, the shared facts, and Candidate Evidence in.
Progress and the accepted evidence variant out. This module does not name the
requirement and does not write the required set. ``r5_required_set`` remains
the writer. HR requirements are not an input.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from backend.app.reference.legal_eligibility_chain import citizenship_class

POLICY_ID = "requirement_resolution.v1"

REQUIREMENT_LEVELS = frozenset({"REQUIRED", "PREFERRED", "NOT_REQUIRED"})

CE_REQUIREMENT = "ce"
CODE95_REQUIREMENT = "code95"

SHARED_VARIANT = "combined_eu_license"
SEPARATE_VARIANT = "separate_license_and_code95"

CE_DOCUMENT_CODES = frozenset(
    {
        "driver_license",
        "driver_license_code95",
        "driver_qualification_card",
        "code95",
    }
)

_APPROVED = frozenset({"approved"})
_IN_REVIEW = frozenset({"pending_review", "selected"})
_CLOSED_VARIANTS = frozenset({SHARED_VARIANT, SEPARATE_VARIANT})


def issuing_evidence_shape(country: str | None) -> str | None:
    """Shared for an EU/EEA/CH licence, separate otherwise. Unknown stays unknown."""

    klass = citizenship_class(country)
    if klass is None:
        return None
    if klass in {"pl", "eu_eea_ch"}:
        return "shared"
    return "separate"


def requirements_named_by_documents(canonical_codes: Iterable[str]) -> list[dict[str, str]]:
    """Recruitment requirements already named by the policy document set.

    A fact that a person holds ADR or a tachograph card names nothing.
    """

    codes = {str(code or "").strip().lower() for code in canonical_codes if str(code or "").strip()}
    named: list[dict[str, str]] = []
    if codes & {"driver_license", "driver_license_code95"}:
        named.append({"requirement_code": CE_REQUIREMENT, "level": "REQUIRED"})
    if codes & {"driver_qualification_card", "code95", "driver_license_code95"}:
        named.append({"requirement_code": CODE95_REQUIREMENT, "level": "REQUIRED"})
    return named


def resolve_recruitment_requirements(
    requirements: Sequence[Mapping[str, Any]],
    facts: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]] | None = None,
    *,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Resolve each named recruitment requirement. Does not invent one."""

    rows = list(evidence or [])
    return [
        resolve_recruitment_requirement(requirement, facts, rows, today=today)
        for requirement in requirements
    ]


def resolve_recruitment_requirement(
    requirement: Mapping[str, Any],
    facts: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]] | None = None,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """One requirement. Progress is a reading. The stored resolution word is unchanged."""

    code = str(requirement.get("requirement_code") or "").strip().lower()
    level = str(requirement.get("level") or "REQUIRED").strip().upper()
    if level not in REQUIREMENT_LEVELS:
        level = "REQUIRED"
    if code not in {CE_REQUIREMENT, CODE95_REQUIREMENT}:
        return _untouched(code, level)
    if level == "NOT_REQUIRED":
        return _row(code, level, applicable=False, progress=None, resolution=None, shape=None, variant=None)
    country = _text(facts.get("licence_issuing_country"))
    shape = issuing_evidence_shape(country)
    variant = _variant(shape)
    accepted = _matching_evidence(code, evidence or [], variant)
    if accepted == "satisfied":
        return _row(code, level, applicable=True, progress="satisfied", resolution="satisfied", shape=shape, variant=variant)
    if accepted == "under_review":
        return _row(
            code,
            level,
            applicable=True,
            progress="under_review",
            resolution="unresolved",
            shape=shape,
            variant=variant,
        )
    if shape is None:
        return _row(code, level, applicable=True, progress="needs_input", resolution="unresolved", shape=None, variant=None)
    if _blocking(code, facts, shape, today=today):
        return _row(code, level, applicable=True, progress="blocking", resolution="blocking", shape=shape, variant=variant)
    documents = _documents_for(code, shape, facts, today=today)
    return _row(
        code,
        level,
        applicable=True,
        progress="needs_evidence",
        resolution="unresolved",
        shape=shape,
        variant=variant,
        document_codes=documents,
    )


def apply_resolution_to_required_set(
    policy_codes: Sequence[str],
    resolutions: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Materialize the recruitment checklist from policy plus resolution.

    CE and Code 95 document codes leave the set until a resolution still needs
    that evidence. Every other policy code stays. Nothing is added from a fact
    the policy did not name.
    """

    pending: list[str] = []
    for row in resolutions:
        if row.get("progress") != "needs_evidence":
            continue
        for code in row.get("document_codes") or []:
            text = str(code or "").strip().lower()
            if text and text not in pending:
                pending.append(text)
    out: list[str] = []
    for raw in policy_codes:
        code = str(raw or "").strip().lower()
        if not code or code in CE_DOCUMENT_CODES or code in out:
            continue
        out.append(code)
    for code in pending:
        if code not in out:
            out.append(code)
    return out


def _untouched(code: str, level: str) -> dict[str, Any]:
    return _row(code, level, applicable=False, progress=None, resolution=None, shape=None, variant=None, resolved=False)


def _row(
    code: str,
    level: str,
    *,
    applicable: bool,
    progress: str | None,
    resolution: str | None,
    shape: str | None,
    variant: str | None,
    document_codes: Sequence[str] = (),
    resolved: bool = True,
) -> dict[str, Any]:
    holds = bool(applicable and level == "REQUIRED" and progress in {"needs_input", "needs_evidence", "under_review", "blocking"})
    return {
        "policy_id": POLICY_ID,
        "requirement_code": code,
        "level": level,
        "applicable": applicable,
        "progress": progress,
        "resolution": resolution,
        "evidence_shape": shape,
        "evidence_variant": variant,
        "document_codes": list(document_codes),
        "holds_entrance": holds,
        "resolved": resolved,
    }


def _variant(shape: str | None) -> str | None:
    if shape == "shared":
        return SHARED_VARIANT
    if shape == "separate":
        return SEPARATE_VARIANT
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    return raw or None


def _documents_for(code: str, shape: str, facts: Mapping[str, Any], *, today: date | None) -> list[str]:
    del facts, today
    if shape == "shared":
        # One licence is the proof of both rows. A blocking row does not reach this.
        return ["driver_license"] if code in {CE_REQUIREMENT, CODE95_REQUIREMENT} else []
    if code == CE_REQUIREMENT:
        return ["driver_license"]
    return ["driver_qualification_card"]


def _blocking(code: str, facts: Mapping[str, Any], shape: str, *, today: date | None) -> bool:
    if code == CE_REQUIREMENT:
        categories = [str(item or "").strip().upper() for item in (facts.get("licence_categories") or [])]
        return bool(categories) and "CE" not in categories
    if shape != "separate":
        return False
    if facts.get("code95_presence") is False:
        return True
    valid_to = _parse_date(facts.get("code95_valid_to"))
    on = today or date.today()
    return valid_to is not None and valid_to < on


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    raw = _text(value)
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _matching_evidence(
    requirement_code: str,
    evidence: Sequence[Mapping[str, Any]],
    variant: str | None,
) -> str | None:
    """``satisfied`` or ``under_review`` when Candidate Evidence already covers the row."""

    satisfied = False
    review = False
    for row in evidence:
        if str(row.get("requirement_code") or "").strip().lower() != requirement_code:
            continue
        status = str(row.get("status") or "").strip().lower()
        if status in {"draft", "rejected", "superseded"}:
            continue
        stored_variant = str(row.get("evidence_variant_code") or "").strip()
        if stored_variant not in _CLOSED_VARIANTS:
            continue
        if variant is not None and stored_variant != variant:
            continue
        documents = row.get("document_ids") or []
        if not isinstance(documents, Sequence) or isinstance(documents, (str, bytes)) or not list(documents):
            continue
        if status in _APPROVED:
            satisfied = True
        elif status in _IN_REVIEW:
            review = True
    if satisfied:
        return "satisfied"
    if review:
        return "under_review"
    return None
