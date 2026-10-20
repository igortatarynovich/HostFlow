"""Professional requirements stay a shadow explanation.

Legacy years deltas keep the CE-threshold path. New predicates merge by
qualified_code and are explained against the professional profile only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.professional_requirement_identity import (
    parse_qualified_code,
    professional_delta,
)
from backend.app.entity_profile.vacancy_overlay_runtime import (
    ERROR_INVALID_DELTA,
    ERROR_OVERLAY_RELAX,
    merge,
)
from backend.app.services.professional_requirements_evaluator import (
    ENFORCEMENT,
    MATCH,
    NEEDS_INFO,
    NEEDS_REVIEW,
    NO_MATCH,
    PREFERRED_NOT_MATCHED,
    PREFERRED_UNKNOWN,
    evaluate_professional_requirements,
)

_EVALUATOR = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "services"
    / "professional_requirements_evaluator.py"
)
_YEARS_CE = "recruitment.candidate.experience.years_ce"


def _overlay(deltas: list[dict]) -> dict:
    return merge(
        DRIVER_CE_PROFILE_CODE,
        None,
        {"delta": deltas},
    )


def _years_delta(value: int) -> dict:
    return {
        "kind": "value",
        "code": "screening.years_ce.min",
        "owner": "vacancy",
        "op": "tighten",
        "predicate": {"qualified_code": _YEARS_CE, "op": ">=", "value": value},
    }


def _aggregate(status: str, days: int | None = None) -> dict:
    return {
        "status": status,
        "days": days,
        "years": None if days is None else days / 365,
        "contributing_employment_ids": ["emp-1"] if days else [],
        "reasons": [],
    }


def _profile(**overrides) -> dict:
    profile = {
        "capabilities": {
            "licence": {"categories": ["CE"], "raw_unmapped": []},
            "code95": {"presence": True},
            "adr": {"presence": None},
            "tachograph": {"presence": False},
        },
        "experience": {
            "aggregates": {
                "total_tenure": _aggregate("calculated", 1825),
                "ce": _aggregate("calculated", 548),
                "eu": _aggregate("presence_only"),
                "international": _aggregate("no_evidence"),
                "movement_pattern": {"long_haul": _aggregate("calculated", 1825)},
                "crew_mode": {"solo": _aggregate("calculated", 1825)},
            },
            "work_character": {"operation_scopes": [{"code": "domestic", "resolution": "catalog"}]},
            "practical_experience": {
                "trailers": {
                    "items": [
                        {"code": "frigo", "mapping": "unmapped", "target_code": None},
                    ]
                }
            },
        },
        "constraints": [],
    }
    profile.update(overrides)
    return profile


def test_legacy_years_delta_stays_on_the_ce_threshold():
    effective = _overlay([
        _years_delta(5),
        professional_delta(
            qualified_code="experience:CE",
            strength="mandatory",
            mode="minimum",
            minimum_days=365,
        ),
    ])
    assert effective["ok"] is True
    assert effective["years_ce_min"] == 5
    assert effective["years_ce_owner"] == "vacancy"
    assert effective["professional_requirements"][0]["qualified_code"] == "experience:CE"
    assert effective["professional_requirements"][0]["minimum_days"] == 365


def test_same_qualified_code_tightens_by_the_stronger_condition():
    effective = _overlay([
        professional_delta(
            qualified_code="experience:CE",
            strength="preferred",
            mode="presence",
        ),
        professional_delta(
            qualified_code="experience:CE",
            strength="mandatory",
            mode="minimum",
            minimum_days=365,
            op="add",
        ),
        professional_delta(
            qualified_code="experience:CE",
            strength="mandatory",
            mode="minimum",
            minimum_days=730,
            op="tighten",
        ),
    ])
    row = effective["professional_requirements"][0]
    assert row["strength"] == "mandatory"
    assert row["mode"] == "minimum"
    assert row["minimum_days"] == 730
    assert effective["years_ce_min"] == 2


def test_weaker_tighten_is_a_relax_and_an_invented_code_is_invalid():
    weaker = _overlay([
        professional_delta(
            qualified_code="experience:total",
            strength="mandatory",
            mode="minimum",
            minimum_days=730,
        ),
        professional_delta(
            qualified_code="experience:total",
            strength="mandatory",
            mode="presence",
            op="tighten",
        ),
    ])
    assert weaker["ok"] is False
    assert weaker["error"] == ERROR_OVERLAY_RELAX

    invented = _overlay([{
        "kind": "value",
        "code": "capability:made_up",
        "owner": "vacancy",
        "op": "add",
        "predicate": {"qualified_code": "capability:made_up", "strength": "mandatory"},
    }])
    assert invented["ok"] is False
    assert invented["error"] == ERROR_INVALID_DELTA
    assert parse_qualified_code("experience:trailer_hiring:other") is None
    assert parse_qualified_code("experience:operation_scope:international") is None


def _result(profile: dict, *deltas: dict) -> dict:
    effective = _overlay(list(deltas))
    assert effective["ok"] is True
    return evaluate_professional_requirements(profile, effective["professional_requirements"])


def _by_code(evaluation: dict) -> dict[str, dict]:
    return {row["qualified_code"]: row for row in evaluation["requirements"]}


def test_scenario_matrix_explains_each_requirement_without_enforcing_it():
    profile = _profile(constraints=[
        {"id": "c-night", "subject": "work_pattern", "code": "night", "effect": "prohibited", "activity": "active"},
        {"id": "c-old", "subject": "work_pattern", "code": "night", "effect": "prohibited", "activity": "expired"},
        {"id": "c-reefer", "subject": "trailer", "code": "reefer", "effect": "limited", "activity": "active"},
        {"id": "c-dump", "subject": "trailer", "code": "dump", "effect": "prohibited", "activity": "unknown"},
        {"id": "c-past", "subject": "route", "code": "ferry", "effect": "prohibited", "activity": "expired"},
    ])
    mapped_profile = _profile(experience={
        "aggregates": {
            "total_tenure": _aggregate("calculated", 1825),
            "ce": _aggregate("presence_only"),
            "eu": _aggregate("calculated", 800),
            "international": _aggregate("ambiguous_history"),
        },
        "work_character": {"operation_scopes": []},
        "practical_experience": {
            "trailers": {
                "items": [{
                    "code": "reefer",
                    "mapping": "mapped",
                    "target_vocabulary": "trailer_hiring",
                    "target_code": "reefer",
                }]
            }
        },
    })
    absent_licence = _profile()
    absent_licence["capabilities"]["licence"] = {"categories": ["C"], "raw_unmapped": []}

    short = _result(
        profile,
        professional_delta(qualified_code="experience:CE", strength="mandatory", mode="minimum", minimum_days=730),
        professional_delta(qualified_code="capability:driving_category:CE", strength="mandatory"),
        professional_delta(qualified_code="capability:adr", strength="mandatory"),
        professional_delta(qualified_code="capability:tachograph", strength="mandatory"),
        professional_delta(qualified_code="experience:trailer_hiring:reefer", strength="mandatory", mode="presence"),
        professional_delta(qualified_code="characteristic:work_pattern:night", strength="mandatory"),
        professional_delta(qualified_code="characteristic:trailer:reefer", strength="mandatory"),
        professional_delta(qualified_code="characteristic:trailer:dump", strength="mandatory"),
        professional_delta(qualified_code="characteristic:route:ferry", strength="mandatory"),
        professional_delta(qualified_code="experience:international", strength="preferred", mode="presence"),
        professional_delta(qualified_code="language:pl", strength="preferred"),
    )
    rows = _by_code(short)
    assert rows["experience:CE"]["result"] == NO_MATCH
    assert rows["experience:CE"]["reason"] == "calculated_below_minimum"
    assert rows["experience:CE"]["evidence"]["days"] == 548
    assert rows["experience:CE"]["provenance"][0]["employment_ids"] == ["emp-1"]
    assert rows["capability:driving_category:CE"]["result"] == MATCH
    assert rows["capability:adr"]["result"] == NEEDS_INFO
    assert rows["capability:tachograph"]["result"] == NO_MATCH
    assert rows["experience:trailer_hiring:reefer"]["result"] == NEEDS_REVIEW
    assert rows["experience:trailer_hiring:reefer"]["reason"] == "trailer_unmapped"
    assert rows["characteristic:work_pattern:night"]["result"] == NO_MATCH
    assert rows["characteristic:trailer:reefer"]["result"] == NEEDS_REVIEW
    assert rows["characteristic:trailer:dump"]["result"] == NEEDS_REVIEW
    assert rows["characteristic:route:ferry"]["result"] == MATCH
    assert rows["experience:international"]["affects_eligibility"] is False
    assert rows["experience:international"]["preference_result"] == PREFERRED_UNKNOWN
    assert rows["language:pl"]["result"] == NEEDS_INFO
    assert rows["language:pl"]["preference_result"] == PREFERRED_UNKNOWN
    assert short["enforcement"] == ENFORCEMENT
    assert short["shadow_eligibility"] == NO_MATCH
    assert "no_fit" not in short

    presence_gap = _result(
        mapped_profile,
        professional_delta(qualified_code="experience:CE", strength="mandatory", mode="minimum", minimum_days=730),
        professional_delta(qualified_code="experience:EU", strength="mandatory", mode="minimum", minimum_days=365),
        professional_delta(qualified_code="experience:EU", strength="mandatory", mode="presence"),
        professional_delta(qualified_code="experience:trailer_hiring:reefer", strength="mandatory", mode="presence"),
        professional_delta(qualified_code="experience:operation_scope:domestic", strength="mandatory", mode="minimum", minimum_days=365),
    )
    gap = _by_code(presence_gap)
    assert gap["experience:CE"]["result"] == NEEDS_INFO
    assert gap["experience:CE"]["reason"] == "presence_only_not_duration"
    assert gap["experience:EU"]["result"] == MATCH
    assert gap["experience:EU"]["expected"]["mode"] == "minimum"
    assert gap["experience:trailer_hiring:reefer"]["result"] == MATCH
    assert gap["experience:operation_scope:domestic"]["result"] == NEEDS_INFO
    assert presence_gap["shadow_eligibility"] == NEEDS_INFO

    preferred_only = _result(
        absent_licence,
        professional_delta(qualified_code="capability:driving_category:CE", strength="preferred"),
    )
    preferred = preferred_only["requirements"][0]
    assert preferred["result"] == NO_MATCH
    assert preferred["preference_result"] == PREFERRED_NOT_MATCHED
    assert preferred["affects_eligibility"] is False
    assert preferred_only["shadow_eligibility"] == MATCH


@pytest.mark.parametrize(
    ("status", "mode", "days", "expected_result"),
    [
        ("no_evidence", "minimum", None, NEEDS_INFO),
        ("insufficient_history", "minimum", None, NEEDS_INFO),
        ("ambiguous_history", "presence", None, NEEDS_INFO),
        ("presence_only", "presence", None, MATCH),
        ("calculated", "minimum", 730, MATCH),
    ],
)
def test_experience_status_never_treats_missing_duration_as_a_shortfall(status, mode, days, expected_result):
    profile = _profile()
    profile["experience"]["aggregates"]["total_tenure"] = _aggregate(status, days)
    evaluation = _result(
        profile,
        professional_delta(
            qualified_code="experience:total",
            strength="mandatory",
            mode=mode,
            minimum_days=365 if mode == "minimum" else None,
        ),
    )
    assert evaluation["requirements"][0]["result"] == expected_result
    if status != "calculated":
        assert evaluation["requirements"][0]["result"] != NO_MATCH


def test_evaluator_does_not_read_legacy_thresholds_or_documents():
    source = _EVALUATOR.read_text(encoding="utf-8")
    for forbidden in (
        "years_ce_min",
        "min_experience_eu_years",
        "evaluate_lead_criteria",
        "lead_criteria",
        "no_fit",
        "modules.documents",
    ):
        assert forbidden not in source
    untouched = evaluate_professional_requirements(
        {"years_ce_min": 0, "experience": {"aggregates": {"ce": _aggregate("calculated", 1)}}},
        [],
    )
    assert untouched["shadow_eligibility"] == MATCH
    assert untouched["requirements"] == []
