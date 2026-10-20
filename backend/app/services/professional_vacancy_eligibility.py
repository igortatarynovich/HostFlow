"""Read projection of professional vacancy eligibility.

Identity is one candidate and one vacancy. The projection reads the vacancy
overlay and the professional profile, calls the existing evaluator, and
writes nothing. A missing vacancy is not an eligibility result.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.vacancy_bridge import resolve_entity_profile_hints_from_vacancy
from backend.app.entity_profile.vacancy_overlay_runtime import merge, resolve_overlay
from backend.app.models.vacancy import Vacancy
from backend.app.modules.leads.lead_criteria_eval import vacancy_extra_as_dict
from backend.app.services.professional_profile import (
    ProfessionalProfileNotFound,
    load_professional_profile,
)
from backend.app.services.professional_requirements_evaluator import (
    CONTRACT_ID,
    ENFORCEMENT,
    evaluate_professional_requirements,
)


class ProfessionalVacancyEligibilityNotFound(Exception):
    """The candidate or the vacancy is not in this tenant."""


def project_professional_vacancy_eligibility(
    profile: Mapping[str, Any] | None,
    vacancy_payload: Mapping[str, Any] | None,
    *,
    candidate_id: str,
    vacancy_id: str,
    profile_code: str | None,
) -> dict[str, Any]:
    """Explain one pair. Does not read leads and does not store a verdict."""

    payload = dict(vacancy_payload or {})
    payload["vacancy_id"] = vacancy_id
    payload["id"] = vacancy_id
    if profile_code:
        payload["profile_code"] = profile_code
    overlay = resolve_overlay(profile_code or "", payload)
    effective = merge(profile_code or "", None, overlay) if overlay.get("ok") is not False else overlay
    if effective.get("ok") is False:
        return {
            "candidate_id": candidate_id,
            "vacancy_id": vacancy_id,
            "contract_id": CONTRACT_ID,
            "enforcement": ENFORCEMENT,
            "unavailable": str(effective.get("error") or "unavailable"),
        }
    evaluation = evaluate_professional_requirements(
        profile,
        effective.get("professional_requirements") or [],
    )
    mandatory = [
        row for row in evaluation["requirements"] if row.get("affects_eligibility")
    ]
    return {
        "candidate_id": candidate_id,
        "vacancy_id": vacancy_id,
        "contract_id": evaluation["contract_id"],
        "enforcement": evaluation["enforcement"],
        "shadow_eligibility": evaluation["shadow_eligibility"],
        "requirements": mandatory,
    }


def _overlay_payload(vacancy: Vacancy) -> dict[str, Any]:
    """Keys the overlay runtime already reads. This function does not write them."""

    extra = vacancy_extra_as_dict(vacancy.extra)
    payload: dict[str, Any] = {}
    if "delta" in extra:
        payload["delta"] = extra["delta"]
    overlay = extra.get("overlay")
    if isinstance(overlay, Mapping):
        payload["overlay"] = dict(overlay)
    return payload


async def load_professional_vacancy_eligibility(
    session: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    vacancy_id: str,
) -> dict[str, Any]:
    """Load the pair and project it. Performs no writes."""

    if not str(vacancy_id or "").strip():
        raise ProfessionalVacancyEligibilityNotFound(candidate_id)
    vacancy = await session.scalar(
        select(Vacancy).where(
            Vacancy.id == str(vacancy_id),
            Vacancy.tenant_id == str(tenant_id),
        )
    )
    if vacancy is None:
        raise ProfessionalVacancyEligibilityNotFound(vacancy_id)
    try:
        profile = await load_professional_profile(
            session,
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
        )
    except ProfessionalProfileNotFound as exc:
        raise ProfessionalVacancyEligibilityNotFound(candidate_id) from exc
    entity_code, _, _ = await resolve_entity_profile_hints_from_vacancy(
        session,
        tenant_id=str(tenant_id),
        vacancy_id=str(vacancy.id),
    )
    return project_professional_vacancy_eligibility(
        profile,
        _overlay_payload(vacancy),
        candidate_id=str(candidate_id),
        vacancy_id=str(vacancy.id),
        profile_code=entity_code,
    )
