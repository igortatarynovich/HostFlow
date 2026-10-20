"""Candidate × Vacancy professional eligibility is a read projection."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.entity_profile.professional_requirement_identity import professional_delta
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.company import Company
from backend.app.models.vacancy import Vacancy
from backend.app.services.professional_vacancy_eligibility import (
    ProfessionalVacancyEligibilityNotFound,
    load_professional_vacancy_eligibility,
    project_professional_vacancy_eligibility,
)

_SERVICE = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "services"
    / "professional_vacancy_eligibility.py"
)


def test_projection_names_the_pair_and_does_not_score_the_candidate() -> None:
    source = _SERVICE.read_text(encoding="utf-8")
    assert "evaluate_lead_criteria_v1" not in source
    assert "overall_result" not in source
    result = project_professional_vacancy_eligibility(
        {"capabilities": {"licence": {"categories": [], "raw_unmapped": []}}},
        {"delta": [professional_delta(qualified_code="capability:driving_category:CE", strength="mandatory")]},
        candidate_id="cand",
        vacancy_id="vac",
        profile_code="recruitment.candidate.driver_ce",
    )
    assert result["candidate_id"] == "cand"
    assert result["vacancy_id"] == "vac"
    assert result["shadow_eligibility"] == "needs_info"
    assert "overall_result" not in result
    assert "fit" not in result
    assert "no_fit" not in result
    assert "stage" not in result


def test_unknown_profile_is_not_an_eligibility_status() -> None:
    result = project_professional_vacancy_eligibility(
        {},
        {},
        candidate_id="cand",
        vacancy_id="vac",
        profile_code=None,
    )
    assert "shadow_eligibility" not in result
    assert result["unavailable"] == "unknown_profile"
    assert result["vacancy_id"] == "vac"


async def _company_id(db, tenant_id: str) -> str:
    found = await db.scalar(select(Company.id).where(Company.tenant_id == tenant_id).limit(1))
    if found:
        return str(found)
    company_id = str(uuid.uuid4())
    db.add(Company(id=company_id, tenant_id=tenant_id, name="Eligibility Co"))
    await db.flush()
    return company_id


def _candidate(candidate_id: str, tenant_id: str, categories: list[str]) -> Candidate:
    return Candidate(
        id=candidate_id,
        tenant_id=tenant_id,
        first_name="Ada",
        last_name="Nowak",
        stage="new",
        extra="{}",
        personal_data={"operator_facts": {"licence_categories": categories}},
        intake_state={},
    )


@pytest.mark.anyio
async def test_read_projection_explains_each_status_without_writing(db) -> None:
    from backend.tests.conftest import DEFAULT_TENANT_ID

    tenant_id = DEFAULT_TENANT_ID
    suffix = uuid.uuid4().hex[:8]
    company_id = await _company_id(db, tenant_id)
    profile_id = str(uuid.uuid4())
    db.add(CandidateProfile(
        id=profile_id,
        tenant_id=tenant_id,
        code="base",
        name="Driver",
        config={},
    ))
    delta = [
        professional_delta(qualified_code="capability:driving_category:CE", strength="mandatory"),
        professional_delta(qualified_code="experience:international", strength="preferred", mode="presence"),
    ]
    vacancy_id = str(uuid.uuid4())
    db.add(Vacancy(
        id=vacancy_id,
        tenant_id=tenant_id,
        company_id=company_id,
        candidate_profile_id=profile_id,
        title="CE driver",
        employment_type="full_time",
        extra=json.dumps({"delta": delta, "lead_criteria_v1": {"min_experience_eu_years": 5}}),
    ))
    ids = {
        "match": str(uuid.uuid4()),
        "no_match": str(uuid.uuid4()),
        "needs_info": str(uuid.uuid4()),
        "needs_review": str(uuid.uuid4()),
    }
    db.add_all([
        _candidate(ids["match"], tenant_id, ["CE"]),
        _candidate(ids["no_match"], tenant_id, ["C"]),
        _candidate(ids["needs_info"], tenant_id, []),
        _candidate(ids["needs_review"], tenant_id, ["ZZ"]),
    ])
    await db.commit()

    seen = {}
    for name, candidate_id in ids.items():
        seen[name] = await load_professional_vacancy_eligibility(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
        )
        assert seen[name]["candidate_id"] == candidate_id
        assert seen[name]["vacancy_id"] == vacancy_id
        assert seen[name]["enforcement"] == "shadow"
        assert all(row["strength"] == "mandatory" for row in seen[name]["requirements"])
        assert "overall_result" not in seen[name]

    assert seen["match"]["shadow_eligibility"] == "match"
    assert seen["no_match"]["shadow_eligibility"] == "no_match"
    assert seen["needs_info"]["shadow_eligibility"] == "needs_info"
    assert seen["needs_review"]["shadow_eligibility"] == "needs_review"

    no_match_id = ids["no_match"]
    candidate = await db.get(Candidate, no_match_id)
    assert candidate is not None
    assert candidate.stage == "new"
    candidate.stage = "interview"
    await db.commit()
    again = await load_professional_vacancy_eligibility(
        db,
        tenant_id=tenant_id,
        candidate_id=no_match_id,
        vacancy_id=vacancy_id,
    )
    await db.refresh(candidate)
    assert candidate.stage == "interview"
    assert again["shadow_eligibility"] == "no_match"
    assert json.loads(candidate.extra) == {}
    vacancy = await db.get(Vacancy, vacancy_id)
    assert vacancy is not None
    assert json.loads(vacancy.extra)["lead_criteria_v1"]["min_experience_eu_years"] == 5


@pytest.mark.anyio
async def test_missing_vacancy_is_not_needs_info(db) -> None:
    from backend.tests.conftest import DEFAULT_TENANT_ID

    tenant_id = DEFAULT_TENANT_ID
    candidate_id = str(uuid.uuid4())
    db.add(_candidate(candidate_id, tenant_id, ["CE"]))
    await db.commit()
    with pytest.raises(ProfessionalVacancyEligibilityNotFound):
        await load_professional_vacancy_eligibility(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            vacancy_id="",
        )
    with pytest.raises(ProfessionalVacancyEligibilityNotFound):
        await load_professional_vacancy_eligibility(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            vacancy_id=str(uuid.uuid4()),
        )
