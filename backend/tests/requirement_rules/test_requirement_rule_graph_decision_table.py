"""Decision-table tests for Requirement Rule Graph (ADR-018 PR 2A.1)."""

from __future__ import annotations

import pytest

from backend.app.requirement_rules.requirement_rule_contract import (
    AlternativeDisposition,
    MatchedAlternative,
    PersonContext,
    RequirementApplicability,
    RuleGraphPlanningInput,
)
from backend.app.requirement_rules.requirement_rule_graph import (
    alternative_disposition,
    plan_requirement_rule_graph,
    requirement_is_applicable,
)

POLICY = "recruitment.driver_ce.pl/v1"


def _plan(citizenship: str, *, matches: tuple[MatchedAlternative, ...] = (), **person_kw) -> object:
    person = PersonContext(citizenship=citizenship, **person_kw)
    return plan_requirement_rule_graph(
        RuleGraphPlanningInput(
            policy_ref=POLICY,
            person=person,
            matched_alternatives=matches,
        )
    )


def test_scenario_1_polish_citizen() -> None:
    result = _plan("pl")
    assert not requirement_is_applicable(result, "labor_market_access")
    assert not requirement_is_applicable(result, "work_authorization_process")
    assert not requirement_is_applicable(result, "driver_attestation")
    assert not requirement_is_applicable(result, "legal_stay_confirmation")
    assert requirement_is_applicable(result, "driver_entitlement")


def test_scenario_2_german_citizen() -> None:
    result = _plan("de")
    assert not requirement_is_applicable(result, "work_authorization_process")
    assert not requirement_is_applicable(result, "residence_authorization_process")
    assert not requirement_is_applicable(result, "driver_attestation")
    assert requirement_is_applicable(result, "labor_market_access")
    assert alternative_disposition(result, "labor_market_access", "free_movement_labor_access") == AlternativeDisposition.matched


def test_scenario_3_belarus_visa_and_work_permit() -> None:
    matches = (
        MatchedAlternative("legal_stay_confirmation", "approved_visa"),
        MatchedAlternative("labor_market_access", "work_permit_document"),
    )
    result = _plan("by", matches=matches, international_haulage=True, community_licence_carrier=True)
    assert requirement_is_applicable(result, "legal_stay_confirmation")
    assert requirement_is_applicable(result, "labor_market_access")
    assert requirement_is_applicable(result, "driver_attestation")
    assert alternative_disposition(result, "legal_stay_confirmation", "approved_residence_card") == AlternativeDisposition.excluded


def test_scenario_4_residence_card_with_labor_access() -> None:
    matches = (MatchedAlternative("labor_market_access", "residence_card_labor_access"),)
    result = _plan("by", matches=matches)
    assert not requirement_is_applicable(result, "work_authorization_process")


def test_scenario_5_residence_card_without_labor_access() -> None:
    matches = (MatchedAlternative("legal_stay_confirmation", "approved_residence_card"),)
    result = _plan("by", matches=matches)
    assert requirement_is_applicable(result, "legal_stay_confirmation")
    assert requirement_is_applicable(result, "labor_market_access")
    assert requirement_is_applicable(result, "work_authorization_process")


def test_scenario_6_eu_licence_ce_with_code95() -> None:
    matches = (MatchedAlternative("professional_qualification", "driver_license_with_code95"),)
    result = _plan("by", matches=matches)
    assert alternative_disposition(result, "professional_qualification", "approved_qualification_card") == AlternativeDisposition.excluded
    assert alternative_disposition(result, "driver_entitlement", "approved_driver_license_ce") == AlternativeDisposition.matched


def test_scenario_7_ce_without_code95() -> None:
    matches = (MatchedAlternative("driver_entitlement", "approved_driver_license_ce"),)
    result = _plan("by", matches=matches)
    qual_alt = alternative_disposition(result, "professional_qualification", "approved_qualification_card")
    assert qual_alt in {AlternativeDisposition.available, AlternativeDisposition.not_selected}


def test_scenario_8_third_country_driver_attestation_dispatch() -> None:
    result = _plan("by", international_haulage=True, community_licence_carrier=True)
    assert requirement_is_applicable(result, "driver_attestation")
    plan = result.requirements["driver_attestation"]
    assert plan.stage_ownership is not None
    assert plan.stage_ownership.blocks_stage == "ready_for_dispatch"
    assert plan.stage_ownership.source_responsibility == "company"


def test_scenario_9_unclassified_voivodeship_decision() -> None:
    from backend.app.document_types.registry import normalize_input_doc_type

    assert normalize_input_doc_type("voivodeship_decision") == "unclassified"
    assert normalize_input_doc_type("decision") == "unclassified"


def test_polish_citizen_never_requires_work_permit_for_non_pl_citizenship() -> None:
    """EU/EEA/CH must not imply work permit for DE citizen working in PL."""
    result = _plan("de")
    plan = result.requirements.get("work_authorization_process")
    assert plan is not None
    assert plan.applicability == RequirementApplicability.not_applicable
