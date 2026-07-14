"""Tests for RequirementPolicy recruitment.driver_ce.pl/v1 (ADR-018 PR 2A / 2A.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.requirement_rules.requirement_policy_registry import (
    default_policy_ref_for_entity_profile,
    get_policy_requirement,
    get_requirement_policy,
    load_registered_policies,
    policy_blocks_stage,
)

POLICY_REF = "recruitment.driver_ce.pl/v1"
POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "requirement_rules"
    / "data"
    / "requirement_policy.recruitment.driver_ce.pl.v1.json"
)


def test_policy_loaded_with_rule_graph_blocks() -> None:
    policy = get_requirement_policy(POLICY_REF)
    assert policy is not None
    assert policy["schema_version"] == "rule_graph.v1"
    assert isinstance(policy.get("applicability_rules"), list)
    assert isinstance(policy.get("dependency_rules"), list)
    assert isinstance(policy.get("requirement_bindings"), list)


def test_driver_ce_entity_profile_maps_to_policy() -> None:
    assert default_policy_ref_for_entity_profile("recruitment.candidate.driver_ce") == POLICY_REF


@pytest.mark.parametrize(
    ("requirement_code", "blocks_stage"),
    [
        ("identity_document", "docs_received"),
        ("driver_entitlement", "docs_received"),
        ("legal_stay_confirmation", "permit_ordered"),
        ("labor_market_access", "ready_for_hire"),
        ("work_authorization_process", "employment_start"),
        ("driver_attestation", "ready_for_dispatch"),
    ],
)
def test_policy_stage_blocking(requirement_code: str, blocks_stage: str) -> None:
    assert policy_blocks_stage(POLICY_REF, requirement_code) == blocks_stage


def test_driver_attestation_owned_by_company() -> None:
    row = get_policy_requirement(POLICY_REF, "driver_attestation")
    assert row is not None
    ownership = row["stage_ownership"]
    assert ownership["source_responsibility"] == "company"
    assert ownership["operational_owner"] == "transport_compliance"


def test_no_voivodeship_decision_requirement_binding() -> None:
    policy = get_requirement_policy(POLICY_REF)
    codes = {_row["requirement_code"] for _row in policy["requirement_bindings"]}
    assert "voivodeship_decision" not in codes


def test_policy_version_immutability_requires_new_file_for_v2() -> None:
    original = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert original["policy_version"] == "v1"
    assert POLICY_REF in load_registered_policies()
