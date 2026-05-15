"""Industry-aware default funnel presets (§2.2)."""

from __future__ import annotations

from backend.app.modules.companies.funnel_presets import (
    business_funnel_presets,
    normalize_industry,
)


def test_normalize_industry() -> None:
    assert normalize_industry("transport_logistics") == "transport_logistics"
    assert normalize_industry("Transport_Logistics") == "transport_logistics"
    assert normalize_industry("unknown") is None


def test_agency_base_without_industry() -> None:
    p = business_funnel_presets("agency", None)
    assert p["candidate"]["name"] == "Candidate Pipeline"
    assert [s[0] for s in p["candidate"]["stages"]][0] == "new"
    assert "docs_wait" in [s[0] for s in p["candidate"]["stages"]]


def test_agency_transport_candidate_longer_chain() -> None:
    p = business_funnel_presets("agency", "transport_logistics")
    codes = [s[0] for s in p["candidate"]["stages"]]
    assert "permit_ordered" in codes
    assert "trip_plan" in codes
    assert p["lead"]["name"] == "Client pipeline — logistics"


def test_employer_healthcare() -> None:
    p = business_funnel_presets("employer", "healthcare")
    codes = [s[0] for s in p["candidate"]["stages"]]
    assert "questionnaire_submitted" in codes
    assert p["candidate"]["name"].startswith("Hiring pipeline")


def test_services_it_leads_only() -> None:
    p = business_funnel_presets("services", "it")
    assert "Discovery" in p["lead"]["stages"][1][1]
    assert p["candidate"]["name"] == "Candidate Pipeline"
