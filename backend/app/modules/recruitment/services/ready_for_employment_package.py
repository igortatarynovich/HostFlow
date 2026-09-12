"""Assemble ``ready_for_employment.v1`` from existing Candidate facts.

Rehosts the RSO-2 package builder/fingerprint. Does not offer Transfer.
Does not treat Fits as Ready. Does not invent a second readiness model.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Final, Mapping

from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy
from backend.app.reference.ready_for_employment import CONTRACT_ID

PREP_KEY: Final[str] = "ready_for_employment_prep_v1"
FITS_DECISION_KEY: Final[str] = "fits_decision_v1"
OPEN_CANDIDATE_NEXT: Final[str] = "open_candidate"
TRANSFER_READY_STAGES: Final[frozenset[str]] = frozenset({"ready_for_handoff", "ready_for_hr"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def package_fingerprint_v1(package: Mapping[str, Any]) -> str:
    """Stable hash of package-critical facts (staleness check on Transfer)."""
    person = _record(package.get("person"))
    target = _record(package.get("target_work"))
    fits = _record(package.get("fits_decision"))
    refs = _record(package.get("context_refs"))
    critical = {
        "contract_id": package.get("contract_id"),
        "tenant_id": _text(package.get("tenant_id")),
        "person_id": _text(person.get("person_id") or person.get("candidate_id")),
        "identity_facts": _record(person.get("identity_facts")),
        "vacancy_id": _text(target.get("vacancy_id")),
        "employer_id": _text(target.get("employer_id")),
        "role": _text(target.get("role")),
        "fits_decision": _text(fits.get("decision")).lower(),
        "application_id": _text(refs.get("application_id")),
        "recruitment_facts": _record(package.get("recruitment_facts")),
        "evidence": _record(package.get("evidence")),
    }
    raw = json.dumps(critical, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_ready_for_employment_package_v1(
    *,
    tenant_id: str,
    application_id: str,
    candidate: Candidate,
    vacancy: Vacancy | None,
    actor_id: str,
    decided_at: str,
    evidence: Mapping[str, Any] | None = None,
    recruitment_facts: Mapping[str, Any] | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    """Assemble package blocks. Does not persist. Does not create handoff."""
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    if not isinstance(personal, dict):
        personal = {}
    identity_facts: dict[str, Any] = {}
    for key in ("citizenship", "first_name", "last_name", "nationality"):
        val = personal.get(key) or getattr(candidate, key, None)
        if val is not None and _text(val):
            identity_facts[key] = val
    if candidate.first_name and "first_name" not in identity_facts:
        identity_facts["first_name"] = candidate.first_name
    if candidate.last_name and "last_name" not in identity_facts:
        identity_facts["last_name"] = candidate.last_name

    vac_id = _text(getattr(vacancy, "id", None) or getattr(candidate, "vacancy_id", None)) or None
    employer_id = _text(getattr(vacancy, "company_id", None) or getattr(candidate, "company_id", None)) or None
    role = _text(getattr(vacancy, "title", None)) or None

    target_work: dict[str, Any] = {}
    if vac_id:
        target_work["vacancy_id"] = vac_id
    if employer_id:
        target_work["employer_id"] = employer_id
    if role:
        target_work["role"] = role

    context_refs: dict[str, Any] = {"application_id": application_id}
    if source_id:
        context_refs["source_id"] = source_id
    if actor_id:
        context_refs["recruiter_id"] = actor_id

    return {
        "contract_id": CONTRACT_ID,
        "tenant_id": tenant_id,
        "person": {
            "person_id": str(candidate.id),
            "candidate_id": str(candidate.id),
            "identity_facts": identity_facts,
        },
        "target_work": target_work,
        "recruitment_facts": dict(recruitment_facts or {}),
        "evidence": dict(evidence or {}),
        "fits_decision": {
            "decision": "fits",
            "decided_at": decided_at,
            "actor_id": actor_id,
        },
        "context_refs": context_refs,
    }


def candidate_stage_is_transfer_ready(stage: Any) -> bool:
    return _text(stage).lower() in TRANSFER_READY_STAGES


__all__ = [
    "PREP_KEY",
    "FITS_DECISION_KEY",
    "OPEN_CANDIDATE_NEXT",
    "TRANSFER_READY_STAGES",
    "package_fingerprint_v1",
    "build_ready_for_employment_package_v1",
    "candidate_stage_is_transfer_ready",
]
