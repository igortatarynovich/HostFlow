"""Resolver Step 2. Read-only projection. No consumer cutover."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.models.professional_profile import CandidateProfessionalConstraint
from backend.app.services.professional_profile import (
    ChoiceFact,
    CompensationFact,
    ConstraintFact,
    EmploymentFact,
    MappingFact,
    ProfessionalProfileNotFound,
    ProfileInputs,
    load_professional_profile,
    resolve_professional_profile,
)
from backend.app.services.professional_profile_legacy_writers import classify_writes

NOW = datetime(2026, 10, 17, 22, 30, tzinfo=timezone.utc)
EU_FIELD = "experience" + "_eu_years"
CE_TOTAL_FIELD = "experience" + "_ce_total"


def _job(job_id: str, **kwargs) -> EmploymentFact:
    payload = dict(
        id=job_id,
        employer_name=job_id,
        country=None,
        position=None,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 12, 31),
        driving_categories=(),
        operation_scopes=(),
        movement_patterns=(),
        crew_modes=(),
        work_areas=(),
        trailer_types=(),
        route_types=(),
        eu_routes=None,
    )
    payload.update(kwargs)
    return EmploymentFact(**payload)


def _profile(**kwargs) -> dict:
    payload = dict(
        candidate_id="cand",
        tenant_id="tenant",
        timezone_name="Europe/Warsaw",
        now=NOW,
        personal_data={},
        extra={},
        intake_state={},
        employments=(),
        constraints=(),
        choices=(),
        compensation=None,
        available_from=None,
        mappings=(),
    )
    payload.update(kwargs)
    return resolve_professional_profile(ProfileInputs(**payload))


def test_overlapping_tenure_counts_shared_days_once() -> None:
    profile = _profile(
        employments=(
            _job("a", start_date=date(2020, 1, 1), end_date=date(2021, 12, 31)),
            _job("b", start_date=date(2021, 1, 1), end_date=date(2022, 12, 31)),
        )
    )
    tenure = profile["experience"]["aggregates"]["total_tenure"]
    assert tenure["status"] == "calculated"
    assert tenure["days"] == 1096
    assert tenure["contributing_employment_ids"] == ["a", "b"]


def test_open_employment_uses_workspace_today_not_utc() -> None:
    profile = _profile(
        timezone_name="Europe/Warsaw",
        employments=(_job("open", start_date=date(2026, 10, 18), end_date=None),),
    )
    tenure = profile["experience"]["aggregates"]["total_tenure"]
    assert tenure["status"] == "calculated"
    assert tenure["days"] == 1
    assert tenure["years"] == "0.0027"


def test_open_employment_without_timezone_is_insufficient() -> None:
    profile = _profile(
        timezone_name=None,
        employments=(_job("open", start_date=date(2020, 1, 1), end_date=None, driving_categories=("CE",)),),
    )
    tenure = profile["experience"]["aggregates"]["total_tenure"]
    ce = profile["experience"]["aggregates"]["ce"]
    assert tenure["status"] == "insufficient_history"
    assert tenure["days"] is None
    assert ce["status"] == "insufficient_history"
    assert ce["reasons"][0]["code"] == "open_period_without_timezone"


def test_invalid_timezone_does_not_fall_back_to_utc() -> None:
    profile = _profile(
        timezone_name="Not/AZone",
        employments=(_job("open", start_date=date(2020, 1, 1), end_date=None),),
    )
    assert profile["experience"]["aggregates"]["total_tenure"]["status"] == "insufficient_history"


def test_ce_and_c_is_presence_without_years() -> None:
    profile = _profile(employments=(_job("mix", driving_categories=("CE", "C")),))
    ce = profile["experience"]["aggregates"]["ce"]
    assert ce["status"] == "presence_only"
    assert ce["years"] is None
    assert ce["presence"] == ["CE"]
    assert ce["reasons"][0]["code"] == "mixed_values"


def test_ce_only_uses_that_interval() -> None:
    profile = _profile(
        employments=(
            _job("ce", start_date=date(2020, 1, 3), end_date=date(2024, 12, 31), driving_categories=("ce",)),
        )
    )
    ce = profile["experience"]["aggregates"]["ce"]
    assert ce["status"] == "calculated"
    assert ce["days"] == 1825
    assert ce["years"] == "5.0000"


def test_mixed_eu_areas_are_presence_without_eu_years() -> None:
    profile = _profile(
        employments=(
            _job(
                "mix",
                work_areas=(("region", "eu"), ("country", "US")),
                country="DE",
                eu_routes=True,
            ),
        )
    )
    eu = profile["experience"]["aggregates"]["eu"]
    assert eu["status"] == "presence_only"
    assert eu["years"] is None
    codes = {(area["kind"], area["code"]) for area in profile["experience"]["geography"]["work_areas"]}
    assert codes == {("region", "eu"), ("country", "US")}
    assert ("country", "DE") not in codes


def test_mixed_scopes_are_presence_without_international_years() -> None:
    profile = _profile(
        employments=(_job("mix", operation_scopes=("international", "domestic")),)
    )
    international = profile["experience"]["aggregates"]["international"]
    assert international["status"] == "presence_only"
    assert international["years"] is None
    assert international["presence"] == ["international"]


def test_legacy_eu_field_equal_to_years_ce_is_declared_ce_not_calculated_eu() -> None:
    profile = _profile(
        extra={EU_FIELD: 7, CE_TOTAL_FIELD: 12},
        intake_state={"experience": {"years_ce": 7}},
        employments=(
            _job(
                "eu",
                start_date=date(2020, 1, 3),
                end_date=date(2024, 12, 31),
                work_areas=(("region", "eu"),),
            ),
        ),
    )
    eu = profile["experience"]["aggregates"]["eu"]
    assert eu["status"] == "calculated"
    assert eu["years"] == "5.0000"
    assert eu["years"] != "7.0000"
    assert profile["experience"]["declared"]["ce"] == {
        "status": "declared",
        "years": "7",
        "origin": "ce_written_as_eu",
    }
    assert profile["experience"]["declared"]["eu"]["status"] == "no_evidence"
    assert profile["provenance"][EU_FIELD]["used_as_calculated_eu"] is False
    assert profile["provenance"][CE_TOTAL_FIELD]["interpreted_as"] == "not_declared_ce"
    assert profile["experience"]["declared"]["ce"]["years"] != profile["provenance"][CE_TOTAL_FIELD]["stored_value"]


def test_eu_label_without_years_ce_is_not_declared_ce() -> None:
    profile = _profile(extra={EU_FIELD: 4})
    assert profile["provenance"][EU_FIELD]["origin"] == "operator_eu_label"
    assert profile["experience"]["declared"]["ce"]["status"] == "no_evidence"
    assert profile["experience"]["aggregates"]["eu"]["status"] == "no_evidence"


def test_mismatched_years_ce_is_ambiguous_not_declared_ce() -> None:
    profile = _profile(extra={EU_FIELD: 4}, intake_state={"experience": {"years_ce": 7}})
    assert profile["provenance"][EU_FIELD]["origin"] == "ambiguous"
    assert profile["experience"]["declared"]["ce"]["years"] is None


def test_trailers_are_presence_only_and_unmapped_codes_stay_raw() -> None:
    profile = _profile(
        employments=(
            _job(
                "long",
                start_date=date(2020, 1, 3),
                end_date=date(2024, 12, 31),
                trailer_types=("tent", "frigo", "Tautliner"),
            ),
        ),
        mappings=(MappingFact("trailer_hiring", "reefer", "trailer_hiring", "reefer"),),
    )
    trailers = profile["experience"]["practical_experience"]["trailers"]
    assert trailers["status"] == "presence_only"
    assert trailers["years"] is None
    assert trailers["days"] is None
    assert [item["code"] for item in trailers["items"]] == ["Tautliner", "frigo", "tent"]
    assert {item["mapping"] for item in trailers["items"]} == {"unmapped"}
    assert all(item["target_code"] is None for item in trailers["items"])


def test_mapped_trailer_keeps_source_and_target_without_years() -> None:
    profile = _profile(
        employments=(_job("row", trailer_types=("tent",)),),
        mappings=(MappingFact("trailer_employment_raw", "tent", "trailer_hiring", "curtain"),),
    )
    item = profile["experience"]["practical_experience"]["trailers"]["items"][0]
    assert item["mapping"] == "mapped"
    assert item["target_code"] == "curtain"
    assert item["status"] == "presence_only"


def test_unknown_scope_stays_raw_presence() -> None:
    profile = _profile(employments=(_job("row", operation_scopes=("cabotage", "international")),))
    international = profile["experience"]["aggregates"]["international"]
    assert international["status"] == "presence_only"
    assert international["raw_presence"] == ["cabotage"]
    assert international["years"] is None
    codes = {item["code"]: item["resolution"] for item in profile["experience"]["work_character"]["operation_scopes"]}
    assert codes["cabotage"] == "unmapped"
    assert codes["international"] == "catalog"


def test_constraint_is_returned_and_medical_presence_creates_none() -> None:
    profile = _profile(
        personal_data={"operator_facts": {"medical_presence": True, "licence_categories": ["CE"]}},
        constraints=(
            ConstraintFact(
                id="c1",
                subject="trailer",
                code="tanker",
                effect="prohibited",
                source="operator_recorded",
                valid_from=date(2026, 1, 1),
                valid_to=None,
                note="not for matching",
            ),
        ),
    )
    assert profile["constraints"] == [
        {
            "id": "c1",
            "subject": "trailer",
            "code": "tanker",
            "effect": "prohibited",
            "source": "operator_recorded",
            "valid_from": "2026-01-01",
            "valid_to": None,
            "note": "not for matching",
            "activity": "active",
            "matching_key": {"subject": "trailer", "code": "tanker", "effect": "prohibited"},
        }
    ]
    assert profile["capabilities"]["licence"]["categories"] == ["CE"]
    assert "constraints" not in profile["capabilities"]


def test_capabilities_ignore_extra_licence_fields() -> None:
    profile = _profile(
        personal_data={"operator_facts": {"licence_categories": ["CE"], "code95_presence": True}},
        extra={"license_categories": ["B"], "has_adr": True},
    )
    assert profile["capabilities"]["source"] == "operator_facts"
    assert profile["capabilities"]["licence"]["categories"] == ["CE"]
    assert profile["capabilities"]["adr"]["presence"] is None
    assert profile["capabilities"]["code95"]["presence"] is True


def test_preferences_come_from_structured_rows() -> None:
    profile = _profile(
        choices=(ChoiceFact(id="p1", subject="work_system", kind=None, code="2_1"),),
        compensation=CompensationFact(amount=Decimal("4500.5"), currency="EUR", period="monthly_fixed"),
        available_from=date(2026, 11, 1),
        extra={"available_from": "2020-01-01"},
    )
    block = profile["preferences_and_availability"]
    assert block["choices"][0]["code"] == "2_1"
    assert block["compensation"]["amount"] == "4500.50"
    assert block["availability"]["available_from"] == "2026-11-01"
    assert block["availability"]["source"] == "candidate_availability"


def test_inverted_interval_is_ambiguous() -> None:
    profile = _profile(
        employments=(_job("bad", start_date=date(2024, 1, 1), end_date=date(2023, 1, 1), driving_categories=("CE",)),)
    )
    assert profile["experience"]["aggregates"]["ce"]["status"] == "ambiguous_history"


def test_combined_overlap_does_not_copy_mixed_years_onto_clear_facets() -> None:
    profile = _profile(
        extra={
            EU_FIELD: 7,
            CE_TOTAL_FIELD: 12,
            "experience_non_eu_years": 5,
        },
        intake_state={"experience": {"years_ce": 7}},
        employments=(
            _job(
                "clear",
                employer_name="Clear Haul",
                country="DE",
                start_date=date(2020, 1, 3),
                end_date=date(2024, 12, 31),
                driving_categories=("CE",),
                operation_scopes=("international",),
                movement_patterns=("long_haul",),
                crew_modes=("solo",),
                work_areas=(("region", "eu"),),
                eu_routes=False,
            ),
            _job(
                "mixed",
                employer_name="Mixed Haul",
                country="PL",
                start_date=date(2023, 1, 1),
                end_date=date(2025, 6, 30),
                driving_categories=("CE", "C"),
                operation_scopes=("international", "domestic"),
                movement_patterns=("long_haul", "distribution"),
                crew_modes=("solo", "double"),
                work_areas=(("region", "eu"), ("country", "US"), ("region", "dach")),
                trailer_types=("frigo", "Tautliner"),
                eu_routes=True,
            ),
        ),
    )
    aggregates = profile["experience"]["aggregates"]
    assert aggregates["total_tenure"]["days"] == 2006
    assert aggregates["total_tenure"]["contributing_employment_ids"] == ["clear", "mixed"]
    assert aggregates["ce"]["reasons"] == [
        {"employment_id": "mixed", "code": "mixed_values", "facet": "driving_categories"}
    ]
    assert aggregates["international"]["reasons"] == [
        {"employment_id": "mixed", "code": "mixed_values", "facet": "operation_scopes"}
    ]
    assert aggregates["eu"]["reasons"] == [
        {"employment_id": "mixed", "code": "mixed_values", "facet": "work_areas"}
    ]
    for name in ("ce", "international", "eu"):
        block = aggregates[name]
        assert block["status"] == "calculated"
        assert block["days"] == 1825
        assert block["years"] == "5.0000"
        assert block["contributing_employment_ids"] == ["clear"]
    assert aggregates["ce"]["days"] != aggregates["total_tenure"]["days"]
    assert aggregates["movement_pattern"]["long_haul"]["contributing_employment_ids"] == ["clear"]
    assert aggregates["movement_pattern"]["distribution"]["status"] == "presence_only"
    assert aggregates["crew_mode"]["solo"]["contributing_employment_ids"] == ["clear"]
    assert aggregates["crew_mode"]["double"]["status"] == "presence_only"
    geography = {(area["kind"], area["code"]) for area in profile["experience"]["geography"]["work_areas"]}
    assert ("country", "DE") not in geography
    assert ("country", "PL") not in geography
    assert ("region", "eu") in geography
    assert ("country", "US") in geography
    assert ("region", "dach") in geography
    dach = next(area for area in profile["experience"]["geography"]["work_areas"] if area["code"] == "dach")
    assert dach["resolution"] == "unmapped"
    trailers = profile["experience"]["practical_experience"]["trailers"]
    assert trailers["status"] == "presence_only"
    assert trailers["years"] is None
    assert [item["code"] for item in trailers["items"]] == ["Tautliner", "frigo"]
    assert profile["experience"]["declared"]["ce"]["years"] == "7"
    assert profile["experience"]["declared"]["ce"]["years"] != aggregates["ce"]["years"]
    assert profile["experience"]["declared"]["eu"]["years"] is None
    assert profile["provenance"][CE_TOTAL_FIELD]["interpreted_as"] == "not_declared_ce"
    employments = {row["id"]: row for row in profile["experience"]["employments"]}
    assert employments["mixed"]["eu_routes"] is True
    assert employments["clear"]["country"] == "DE"


def test_same_inputs_are_deterministic() -> None:
    kwargs = dict(
        employments=(
            _job("b", driving_categories=("C", "CE"), work_areas=(("country", "us"), ("region", "EU"))),
            _job("a", driving_categories=("CE",)),
        )
    )
    assert _profile(**kwargs) == _profile(**kwargs)


def test_expired_constraint_uses_workspace_today() -> None:
    profile = _profile(
        constraints=(
            ConstraintFact(
                id="old",
                subject="route",
                code="night",
                effect="limited",
                source="operator_recorded",
                valid_from=date(2020, 1, 1),
                valid_to=date(2026, 10, 17),
                note=None,
            ),
        )
    )
    assert profile["constraints"][0]["activity"] == "expired"


def test_constraint_activity_is_unknown_without_timezone() -> None:
    profile = _profile(
        timezone_name=None,
        constraints=(
            ConstraintFact(
                id="open",
                subject="route",
                code="night",
                effect="limited",
                source="operator_recorded",
                valid_from=None,
                valid_to=date(2020, 1, 1),
                note=None,
            ),
        ),
    )
    assert profile["constraints"][0]["activity"] == "unknown"


def test_candidate_profile_on_resolver_does_not_retire_the_ce_bridge() -> None:
    from backend.app.services.professional_profile_legacy_writers import (
        CANDIDATE_PROFILE_ON_RESOLVER,
        LEGACY_WRITERS,
    )

    assert CANDIDATE_PROFILE_ON_RESOLVER is True
    bridge = next(
        writer
        for writer in LEGACY_WRITERS
        if writer.owner == "backend/app/api/public/intake.py" and writer.target_legacy_field == "experience_eu_years"
    )
    assert bridge.retirement_status == "still_required"


def test_resolver_adds_no_legacy_writer() -> None:
    unclassified, missing, removable = classify_writes()
    assert unclassified == []
    assert missing == []
    assert removable == []


@pytest.mark.anyio
async def test_loader_is_read_only_and_tenant_scoped(db) -> None:
    from backend.tests.conftest import DEFAULT_TENANT_ID

    suffix = uuid.uuid4().hex[:8]
    tenant_id = DEFAULT_TENANT_ID
    other_tenant_id = "22222222-2222-2222-2222-222222222222"
    candidate_id = f"pp-cand-{suffix}"
    other_candidate_id = f"pp-other-cand-{suffix}"
    extra = {EU_FIELD: 7, CE_TOTAL_FIELD: 99, "license_categories": ["B"]}
    personal = {"operator_facts": {"licence_categories": ["CE"], "medical_presence": True}}
    intake = {"experience": {"years_ce": 7}}
    candidate = Candidate(
        id=candidate_id,
        tenant_id=tenant_id,
        first_name="Ada",
        last_name="Nowak",
        extra=json.dumps(extra),
        personal_data=personal,
        intake_state=intake,
    )
    other = Candidate(
        id=other_candidate_id,
        tenant_id=tenant_id,
        first_name="Other",
        last_name="Person",
        extra="{}",
        personal_data={},
        intake_state={},
    )
    employment = CandidateEmployment(
        id=f"pp-job-{suffix}",
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        employer_name="Clear",
        country="DE",
        start_date=date(2020, 1, 3),
        end_date=date(2024, 12, 31),
        driving_categories=["CE"],
        operation_scopes=["international"],
        work_areas=[{"kind": "region", "code": "eu"}],
        trailer_types=["Tautliner"],
        eu_routes=True,
    )
    leaked = CandidateProfessionalConstraint(
        id=f"pp-leak-{suffix}",
        tenant_id=tenant_id,
        candidate_id=other_candidate_id,
        subject="vehicle",
        code="bus",
        effect="prohibited",
        source="operator_recorded",
    )
    own = CandidateProfessionalConstraint(
        id=f"pp-own-{suffix}",
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        subject="route",
        code="night",
        effect="limited",
        source="operator_recorded",
    )
    db.add_all([candidate, other, employment, leaked, own])
    await db.commit()

    profile = await load_professional_profile(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        now=NOW,
    )
    assert profile["experience"]["aggregates"]["ce"]["years"] == "5.0000"
    assert profile["experience"]["declared"]["ce"]["years"] == "7"
    assert profile["constraints"][0]["code"] == "night"
    assert profile["capabilities"]["licence"]["categories"] == ["CE"]
    assert ("country", "DE") not in {
        (area["kind"], area["code"]) for area in profile["experience"]["geography"]["work_areas"]
    }

    with pytest.raises(ProfessionalProfileNotFound):
        await load_professional_profile(db, tenant_id=other_tenant_id, candidate_id=candidate_id, now=NOW)

    await db.refresh(candidate)
    await db.refresh(employment)
    assert json.loads(candidate.extra) == extra
    assert candidate.personal_data["operator_facts"]["licence_categories"] == ["CE"]
    assert employment.driving_categories == ["CE"]
    assert employment.eu_routes is True
    stored_constraint = await db.scalar(
        select(CandidateProfessionalConstraint).where(CandidateProfessionalConstraint.id == own.id)
    )
    assert stored_constraint is not None
    assert stored_constraint.code == "night"
