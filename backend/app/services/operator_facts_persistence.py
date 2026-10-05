"""Persist operator facts on the candidate and refresh the legal chain reading."""

from __future__ import annotations

import json
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.candidate import Candidate
from backend.app.models.hr_employment import Employment
from backend.app.services.hr_legal_eligibility_gate import (
    evaluate_hr_legal_eligibility_gate,
    record_hr_legal_eligibility_gate,
)
from backend.app.services.operator_facts_surface import (
    OperatorFactsRejected,
    apply_operator_facts_patch,
    build_operator_facts_view,
    chain_reading,
    facts_from_personal_data,
    personal_data_with_facts,
)
from backend.app.services.workforce_employees import find_employee_by_candidate


async def preparing_employment_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> Employment | None:
    employee = await find_employee_by_candidate(db, tenant_id, candidate_id)
    if employee is None:
        return None
    res = await db.execute(
        select(Employment)
        .where(
            Employment.tenant_id == tenant_id,
            Employment.employee_id == str(employee.id),
            Employment.state == "preparing",
        )
        .order_by(Employment.created_at.desc())
    )
    return res.scalars().first()


def _extra_dict(candidate: Candidate) -> dict[str, Any]:
    raw = candidate.extra
    if isinstance(raw, dict):
        return dict(raw)
    try:
        return json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _mirror_existing_fields(extra: dict[str, Any], facts: Mapping[str, Any]) -> dict[str, Any]:
    """Keep the legacy mirrors the card already reads. They are not a second owner."""

    if facts.get("citizenship"):
        extra["citizenship"] = facts["citizenship"]
    else:
        extra.pop("citizenship", None)
    presence = facts.get("adr_presence")
    if isinstance(presence, bool):
        extra["has_adr"] = presence
    else:
        extra.pop("has_adr", None)
    return extra


async def save_operator_facts(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    patch: Mapping[str, Any],
    actor_user_id: str,
    employment_id: str | None = None,
) -> dict[str, Any]:
    personal = candidate.personal_data if isinstance(candidate.personal_data, dict) else {}
    current = facts_from_personal_data(personal)
    employment = None
    if employment_id:
        employment = await db.get(Employment, employment_id)
        if employment is None or str(employment.tenant_id) != str(tenant_id):
            raise OperatorFactsRejected("employment is not in this tenant")
    else:
        employment = await preparing_employment_for_candidate(
            db, tenant_id=tenant_id, candidate_id=str(candidate.id)
        )
    bound_employment = str(employment.id) if employment is not None else None
    facts = apply_operator_facts_patch(current, patch, employment_id=bound_employment)
    candidate.personal_data = personal_data_with_facts(personal, facts)
    flag_modified(candidate, "personal_data")
    extra = _mirror_existing_fields(_extra_dict(candidate), facts)
    candidate.extra = json.dumps(extra)
    legal: dict[str, Any] | None = None
    if employment is not None:
        reading = chain_reading(facts, employment_id=str(employment.id))
        result = await record_hr_legal_eligibility_gate(
            db,
            tenant_id=tenant_id,
            employment=employment,
            reading=reading,
            actor_user_id=actor_user_id,
        )
        legal = {
            "outcome": result.outcome,
            "policy_id": result.policy_id,
            "applies": result.applies,
            "recorded": result.applies,
            "chain": result.chain,
        }
    else:
        reading = chain_reading(facts, employment_id=None)
        evaluated = evaluate_hr_legal_eligibility_gate(
            employment_state="preparing",
            reading=reading,
            client_company_id=None,
            vacancy_id=None,
            planned_start=None,
        )
        legal = {
            "outcome": evaluated.outcome,
            "policy_id": evaluated.policy_id,
            "applies": False,
            "recorded": False,
            "chain": evaluated.chain,
        }
    await db.commit()
    view = build_operator_facts_view(facts, employment_id=bound_employment)
    view["legal_eligibility"] = legal
    return view


def operator_facts_view_for_candidate(
    candidate: Candidate,
    *,
    employment_id: str | None = None,
) -> dict[str, Any]:
    personal = candidate.personal_data if isinstance(candidate.personal_data, dict) else {}
    facts = facts_from_personal_data(personal)
    view = build_operator_facts_view(facts, employment_id=employment_id)
    view["legal_eligibility"] = None
    return view
