"""Assemble Vacancy Requirements verdict for a Recruitment Application.

Maps Lead/Candidate transport into canonical occupancy via Mapping convert
projection, then evaluates Overlay merge × facts. Never uses lead_criteria.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.vacancy_bridge import (
    resolve_entity_profile_hints_from_vacancy,
)
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.vacancy import Vacancy
from backend.app.modules.leads.conversion_mapping import apply_executable_intake_mapping
from backend.app.reference.vacancy_requirements import evaluate_vacancy_requirements_v1


def _vacancy_overlay_payload(vacancy: Vacancy | None) -> dict[str, Any]:
    if vacancy is None:
        return {}
    payload: dict[str, Any] = {"vacancy_ref": str(vacancy.id)}
    extra = getattr(vacancy, "extra", None)
    if isinstance(extra, dict):
        # Overlay operator write may later persist delta here; ad-hoc keys map in runtime.
        if isinstance(extra.get("delta"), list):
            payload["delta"] = extra["delta"]
        if extra.get("years_ce_min") is not None:
            payload["years_ce_min"] = extra.get("years_ce_min")
        for key in ("extra_document_types", "add_document_types"):
            if extra.get(key):
                payload[key] = extra.get(key)
        overlay = extra.get("entity_profile_vacancy_overlay.v1") or extra.get(
            "vacancy_overlay"
        )
        if isinstance(overlay, dict) and isinstance(overlay.get("delta"), list):
            payload["delta"] = overlay["delta"]
    return payload


def _facts_from_lead(lead: Lead) -> Any:
    """Project transport → canonical occupancy shape via Mapping (not decision authority)."""
    normalized = getattr(lead, "normalized", None)
    mapped = apply_executable_intake_mapping(
        normalized if isinstance(normalized, dict) else {}
    )
    personal = dict(mapped.personal)
    extra = dict(mapped.extra)
    # Prefer already-converted column mirrors when present.
    for attr, key in (
        ("first_name", "first_name"),
        ("last_name", "last_name"),
        ("phone", "phone"),
        ("email", "email"),
    ):
        val = getattr(lead, attr, None)
        if val and key not in personal:
            personal[key] = val
    return SimpleNamespace(
        personal_data=personal,
        extra=extra,
        first_name=getattr(lead, "first_name", None),
        last_name=getattr(lead, "last_name", None),
        phone=getattr(lead, "phone", None),
        email=getattr(lead, "email", None),
        _get_personal_data=lambda: personal,
        _get_extra=lambda: extra,
    )


async def build_requirements_verdict_for_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    evidence_document_types: list[str] | None = None,
) -> Optional[dict[str, Any]]:
    vacancy_id = str(getattr(lead, "vacancy_id", None) or "").strip()
    if not vacancy_id:
        return {
            "ok": True,
            "contract_id": "vacancy_recruitment_requirements.v1",
            "status": "missing",
            "explanation": [
                {
                    "kind": "vacancy",
                    "code": "vacancy.unbound",
                    "outcome": "missing",
                    "message": "Application is not bound to a vacancy.",
                }
            ],
            "next_action": {
                "code": "collect_fact",
                "fact_code": "vacancy_id",
                "message": "Confirm vacancy before evaluating fit.",
            },
        }

    vacancy = await db.get(Vacancy, vacancy_id)
    if vacancy is None or str(getattr(vacancy, "tenant_id", "")) != str(tenant_id):
        return {
            "ok": False,
            "contract_id": "vacancy_recruitment_requirements.v1",
            "status": "missing",
            "explanation": [
                {
                    "kind": "vacancy",
                    "code": "vacancy.not_found",
                    "outcome": "missing",
                    "message": "Vacancy not found for this Application.",
                }
            ],
            "next_action": {
                "code": "collect_fact",
                "fact_code": "vacancy_id",
                "message": "Bind a valid vacancy.",
            },
        }

    entity_code, _legacy_id, _legacy_code = await resolve_entity_profile_hints_from_vacancy(
        db, tenant_id=str(tenant_id), vacancy_id=vacancy_id
    )
    profile_code = entity_code or DRIVER_CE_PROFILE_CODE

    candidate_id = str(getattr(lead, "candidate_id", None) or "").strip()
    facts_source: Any
    if candidate_id:
        cand = await db.get(Candidate, candidate_id)
        facts_source = cand if cand is not None else _facts_from_lead(lead)
    else:
        facts_source = _facts_from_lead(lead)

    return evaluate_vacancy_requirements_v1(
        profile=profile_code,
        vacancy=_vacancy_overlay_payload(vacancy),
        facts_source=facts_source,
        evidence_document_types=evidence_document_types or [],
    )
