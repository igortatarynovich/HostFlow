"""Vacancy Requirements Evaluator Gate — four named classes.

Contract: docs/specs/tasks/vacancy-requirements-evaluator.md
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.field_registry.canonical_facts import (
    project_identity_facts_from_candidate,
    read_years_ce,
)
from backend.app.modules.leads.conversion_mapping import apply_executable_intake_mapping
from backend.app.reference.vacancy_requirements import (
    NEXT_COLLECT,
    NEXT_FITS,
    NEXT_REJECT,
    STATUS_FIT,
    STATUS_MISSING,
    STATUS_NOT_FIT,
    evaluate_vacancy_requirements_v1,
)

_PACK_DOCS = ("passport", "driver_license", "code95", "tacho_card")


def _facts(*, years_ce: float | None = 3, citizenship: str | None = "PL") -> SimpleNamespace:
    personal: dict = {}
    if citizenship:
        personal["citizenship"] = citizenship
    extra: dict = {}
    if years_ce is not None:
        extra["experience"] = {"years_ce": years_ce}

    def _get_personal_data() -> dict:
        return personal

    def _get_extra() -> dict:
        return extra

    return SimpleNamespace(
        personal_data=personal,
        extra=extra,
        first_name="Ada",
        last_name="Kowalska",
        _get_personal_data=_get_personal_data,
        _get_extra=_get_extra,
    )


def test_all_requirements_met_is_fit() -> None:
    result = evaluate_vacancy_requirements_v1(
        profile=DRIVER_CE_PROFILE_CODE,
        vacancy={"vacancy_ref": "v-fit"},
        facts_source=_facts(years_ce=3),
        evidence_document_types=_PACK_DOCS,
    )
    assert result["ok"] is True
    assert result["status"] == STATUS_FIT
    assert result["next_action"]["code"] == NEXT_FITS
    assert all(row.get("outcome") == STATUS_FIT for row in result["explanation"])


def test_required_fact_missing() -> None:
    result = evaluate_vacancy_requirements_v1(
        profile=DRIVER_CE_PROFILE_CODE,
        vacancy={"vacancy_ref": "v-missing"},
        facts_source=_facts(years_ce=None),
        evidence_document_types=_PACK_DOCS,
    )
    assert result["status"] == STATUS_MISSING
    assert result["next_action"]["code"] == NEXT_COLLECT
    # Machine key = canonical fact; UI text = human requirement (not overlay/source).
    assert result["next_action"]["fact_code"] == "recruitment.candidate.experience.years_ce"
    assert result["next_action"]["requirement"] == "EU C+E experience (years)"
    assert "years_ce.missing" not in str(result["next_action"]["requirement"])
    assert "field_answers" not in str(result["next_action"])
    missing_rows = [row for row in result["explanation"] if row.get("outcome") == STATUS_MISSING]
    assert missing_rows
    assert all(row.get("qualified_code") or row.get("document_type_code") for row in missing_rows)
    assert all(row.get("requirement") for row in missing_rows)
    assert all("." not in str(row.get("requirement") or "") or "C+E" in str(row.get("requirement")) for row in missing_rows)


def test_hard_mismatch_years_ce_below_min() -> None:
    result = evaluate_vacancy_requirements_v1(
        profile=DRIVER_CE_PROFILE_CODE,
        vacancy={"vacancy_ref": "v-not-fit", "years_ce_min": 2},
        facts_source=_facts(years_ce=1),
        evidence_document_types=_PACK_DOCS,
    )
    assert result["status"] == STATUS_NOT_FIT
    assert result["next_action"]["code"] == NEXT_REJECT
    assert any(row.get("code") == "years_ce.below_min" for row in result["explanation"])


def test_source_independent_canonical_facts() -> None:
    via_answers = apply_executable_intake_mapping(
        {
            "field_answers": [
                {
                    "name": "какой у вас опыт работы водителем c+e в международных перевозках по ес?",
                    "values": ["3"],
                },
                {"name": "гражданство", "values": ["PL"]},
            ]
        }
    )
    via_flat = apply_executable_intake_mapping(
        {"experience_eu_years": 3, "citizenship": "PL"}
    )

    results = []
    for mapped in (via_answers, via_flat):
        cand = _facts(years_ce=None, citizenship=None)
        cand.personal_data.update(mapped.personal)
        cand.extra.update(mapped.extra)
        assert float(read_years_ce(cand)) == 3.0
        assert project_identity_facts_from_candidate(cand).get("citizenship") == "PL"
        results.append(
            evaluate_vacancy_requirements_v1(
                profile=DRIVER_CE_PROFILE_CODE,
                vacancy={"vacancy_ref": "v-src"},
                facts_source=cand,
                evidence_document_types=_PACK_DOCS,
            )
        )

    assert {r["status"] for r in results} == {STATUS_FIT}
    assert all(r["next_action"]["code"] == NEXT_FITS for r in results)

    # Transport bags alone are not authority.
    bag_only = evaluate_vacancy_requirements_v1(
        profile=DRIVER_CE_PROFILE_CODE,
        vacancy={"vacancy_ref": "v-bag"},
        facts_source={
            "field_answers": [{"name": "гражданство", "values": ["PL"]}],
            "normalized": {"documents": list(_PACK_DOCS), "experience_eu_years": 3},
            "documents": list(_PACK_DOCS),
            "nationality": "PL",
            "country": "PL",
        },
        evidence_document_types=[],
    )
    assert bag_only["status"] == STATUS_MISSING


def test_evaluator_does_not_use_lead_criteria_or_normalized_authority() -> None:
    root = Path(__file__).resolve().parents[2] / "app"
    text = (root / "reference" / "vacancy_requirements.py").read_text(encoding="utf-8")
    forbidden = (
        "evaluate_lead_criteria",
        "lead_criteria_v1",
        'field_answers',
        "normalized.documents",
    )
    for pat in forbidden:
        assert pat not in text, f"evaluator still references {pat!r}"


def test_evaluator_does_not_create_candidate_or_transfer() -> None:
    text = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "reference"
        / "vacancy_requirements.py"
    ).read_text(encoding="utf-8")
    for pat in ("create_candidate", "ready_for_employment", "Candidate("):
        assert pat not in text
