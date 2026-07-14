"""Tests for RequirementDefinition registry and alternatives (ADR-018 PR 2A / 2A.1)."""

from __future__ import annotations

import pytest

from backend.app.requirement_rules.requirement_definition_registry import (
    get_requirement_definition_v1,
    list_requirement_definitions_v1,
    requirement_definitions_by_code,
)


REQUIRED_CODES = {
    "identity_document",
    "legal_stay_confirmation",
    "labor_market_access",
    "work_authorization_process",
    "residence_authorization_process",
    "driver_entitlement",
    "professional_qualification",
    "tachograph_eligibility",
    "medical_fitness",
    "psychological_fitness",
    "driver_attestation",
}


def test_all_canonical_requirement_codes_present() -> None:
    codes = set(requirement_definitions_by_code().keys())
    assert REQUIRED_CODES <= codes


@pytest.mark.parametrize("requirement_code", sorted(REQUIRED_CODES))
def test_each_requirement_has_alternatives_with_conditions(requirement_code: str) -> None:
    definition = get_requirement_definition_v1(requirement_code)
    assert definition is not None
    alts = definition.get("alternatives") or []
    assert len(alts) >= 1
    for alt in alts:
        assert alt.get("alternative_code")
        conditions = alt.get("conditions") or []
        assert len(conditions) >= 1
        for cond in conditions:
            assert cond.get("kind")


def test_labor_market_access_includes_free_movement() -> None:
    definition = get_requirement_definition_v1("labor_market_access")
    assert definition is not None
    codes = {alt["alternative_code"] for alt in definition["alternatives"]}
    assert "free_movement_labor_access" in codes


def test_no_universal_voivodeship_decision_requirement() -> None:
    assert get_requirement_definition_v1("voivodeship_decision") is None


def test_driver_attestation_company_owned_process() -> None:
    definition = get_requirement_definition_v1("driver_attestation")
    assert definition is not None
    assert definition.get("business_purpose") == "transport_compliance"


def test_professional_qualification_has_embedded_code95_path() -> None:
    definition = get_requirement_definition_v1("professional_qualification")
    codes = {alt["alternative_code"] for alt in definition["alternatives"]}
    assert "driver_license_with_code95" in codes


def test_list_definitions_non_empty() -> None:
    assert len(list_requirement_definitions_v1()) == len(REQUIRED_CODES)
