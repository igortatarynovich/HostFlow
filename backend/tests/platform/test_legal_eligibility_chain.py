"""Recruitment and HR share one legal-eligibility vocabulary and one country class."""

from __future__ import annotations

from backend.app.reference.country_registry import list_country_registry_entries
from backend.app.reference.early_employability import EU_EEA_CH_ALPHA2
from backend.app.reference.legal_eligibility_chain import (
    OPERATOR_STAY_CHOICES,
    STAY_BASIS,
    citizenship_class,
    eu_eea_ch_alpha2,
)
from backend.app.reference.requirement_resolution import issuing_evidence_shape
from backend.app.services.hr_legal_eligibility_gate import _CITIZENSHIP, _STAY, _WORK
from backend.app.services.operator_facts_surface import build_operator_facts_view, empty_facts


def test_citizenship_class_reads_the_country_registry() -> None:
    assert citizenship_class(None) is None
    assert citizenship_class("  ") is None
    assert citizenship_class("ZZ") is None
    assert citizenship_class("pl") == "pl"
    assert citizenship_class("DE") == "eu_eea_ch"
    assert citizenship_class("CH") == "eu_eea_ch"
    assert citizenship_class("IS") == "eu_eea_ch"
    assert citizenship_class("UA") == "third_country"


def test_eu_eea_ch_is_eu_members_plus_schengen() -> None:
    expected = frozenset(
        entry.identity.alpha2
        for entry in list_country_registry_entries()
        if entry.classifications.eu_member or entry.classifications.schengen_member
    )
    assert eu_eea_ch_alpha2() == expected
    assert EU_EEA_CH_ALPHA2 == expected
    assert "PL" in expected
    assert "CH" in expected
    assert "UA" not in expected


def test_operator_stay_choices_are_the_chain_without_the_determined_value() -> None:
    assert "not_required" in STAY_BASIS
    assert "not_required" not in OPERATOR_STAY_CHOICES
    assert set(OPERATOR_STAY_CHOICES) <= set(STAY_BASIS)
    assert set(_STAY) == set(STAY_BASIS)
    assert _CITIZENSHIP == ("pl", "eu_eea_ch", "third_country")
    assert _WORK == ("not_required", "included_in_stay", "separate_required")


def test_issuing_shape_follows_the_same_class() -> None:
    assert issuing_evidence_shape(None) is None
    assert issuing_evidence_shape("PL") == "shared"
    assert issuing_evidence_shape("NO") == "shared"
    assert issuing_evidence_shape("UA") == "separate"


def test_operator_view_publishes_the_shared_choices() -> None:
    view = build_operator_facts_view(empty_facts())
    assert tuple(view["stay_choices"]) == OPERATOR_STAY_CHOICES
    assert view["work_choices"][0] == "work_permit"
    assert "no_right" in view["work_choices"]
