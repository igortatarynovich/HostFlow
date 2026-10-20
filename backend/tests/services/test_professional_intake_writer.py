"""Intake declarations land on canonical facts and do not invent a job."""

from __future__ import annotations

import json
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.modules.leads.conversion_mapping import conversion_payload_from_normalized
from backend.app.services.professional_intake_writer import (
    normalize_intake_professional_facts,
    record_intake_professional_facts,
)
from backend.app.services.professional_profile import load_professional_profile


def test_bucket_answers_and_free_text_categories_are_dropped() -> None:
    facts = normalize_intake_professional_facts(
        {
            "ce_years": "1-2",
            "licence_categories": ["C+E", "CE"],
            "trailer_codes": ["tent", "mega"],
            "international": "да",
            "code95_presence": "yes",
            "adr_presence": "no",
            "available_from": "2026-11-01",
        }
    )
    assert "ce_years" not in facts
    assert facts["licence_categories"] == ["CE"]
    assert facts["trailer_codes"] == ["curtain"]
    assert facts["international"] is True
    assert facts["code95_presence"] is True
    assert facts["adr_presence"] is False
    assert facts["available_from"] == date(2026, 11, 1)


def test_conversion_keeps_professional_answers_out_of_extra() -> None:
    payload = conversion_payload_from_normalized(
        {
            "canonical_facts_v1": {
                "recruitment.candidate.professional.ce_years": 4,
                "recruitment.candidate.professional.licence_categories": ["CE"],
                "recruitment.candidate.experience.years_ce": 2,
            }
        }
    )
    assert payload["professional"]["ce_years"] == 4
    assert payload["professional"]["licence_categories"] == ["CE"]
    assert payload["extra"]["experience_eu_years"] == 2
    assert "ce_years" not in payload["extra"]
    assert "licence_categories" not in payload["extra"]


@pytest.mark.anyio
async def test_intake_writer_does_not_create_employment(db) -> None:
    from backend.tests.conftest import DEFAULT_TENANT_ID

    suffix = uuid.uuid4().hex[:8]
    candidate = Candidate(
        id=f"intake-decl-{suffix}",
        tenant_id=DEFAULT_TENANT_ID,
        first_name="Test",
        last_name="Driver",
        extra=json.dumps({"experience_eu_years": 2}),
        personal_data={},
        intake_state={},
    )
    db.add(candidate)
    await db.commit()

    await record_intake_professional_facts(
        db,
        tenant_id=DEFAULT_TENANT_ID,
        candidate=candidate,
        facts={
            "licence_categories": ["CE"],
            "code95_presence": True,
            "adr_presence": True,
            "ce_years": 4,
            "international": True,
            "trailer_codes": ["tent"],
            "available_from": "2026-11-01",
        },
    )
    await db.commit()

    jobs = (
        await db.scalars(
            select(CandidateEmployment).where(CandidateEmployment.candidate_id == candidate.id)
        )
    ).all()
    assert jobs == []
    await db.refresh(candidate)
    assert json.loads(candidate.extra)["experience_eu_years"] == 2
    assert "intl_experience" not in json.loads(candidate.extra)

    profile = await load_professional_profile(
        db,
        tenant_id=DEFAULT_TENANT_ID,
        candidate_id=candidate.id,
    )
    assert profile["capabilities"]["licence"]["categories"] == ["CE"]
    assert profile["capabilities"]["code95"]["presence"] is True
    assert profile["capabilities"]["adr"]["presence"] is True
    assert profile["experience"]["declared"]["ce"]["origin"] == "candidate_intake"
    assert profile["experience"]["declared"]["ce"]["years"] == "4"
    assert profile["experience"]["aggregates"]["total_tenure"]["status"] == "no_evidence"
    assert profile["experience"]["declared"]["intake"]["international"] is True
    assert profile["experience"]["declared"]["intake"]["trailers"][0]["target_code"] == "curtain"
    assert profile["preferences_and_availability"]["availability"]["available_from"] == "2026-11-01"
