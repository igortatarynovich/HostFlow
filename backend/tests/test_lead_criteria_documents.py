"""Lead fit vs Documents module (requires_candidate_documents_v1)."""

from __future__ import annotations

import pytest

from backend.app.modules.leads.lead_criteria_eval import (
    DEFAULT_CANDIDATE_DOCUMENT_OK_STATUSES,
    evaluate_lead_criteria_v1,
    evaluate_vacancy_for_lead,
    lead_fit_evaluation_effective,
)


def test_module_branch_skipped_when_not_configured():
    st, rs = evaluate_lead_criteria_v1(
        {},
        {"requires_candidate_documents_v1": []},
        candidate_document_statuses=None,
    )
    # Non-empty criteria object but no active clauses → no reasons → fit (not "no_criteria").
    assert st == "fit"
    assert rs == []


def test_no_candidate_context_needs_info():
    st, rs = evaluate_lead_criteria_v1(
        {"country": "PL"},
        {"requires_candidate_documents_v1": ["driver_license"]},
        candidate_document_statuses=None,
    )
    assert st == "needs_info"
    assert "documents_module_no_candidate" in rs


def test_missing_doc_row():
    st, rs = evaluate_lead_criteria_v1(
        {},
        {"requires_candidate_documents_v1": ["driver_license"]},
        candidate_document_statuses={},
    )
    assert st == "needs_info"
    assert any(x.startswith("candidate_doc_missing:") for x in rs)


def test_bad_status_no_fit():
    st, rs = evaluate_lead_criteria_v1(
        {},
        {"requires_candidate_documents_v1": ["driver_license"]},
        candidate_document_statuses={"driver_license": ["rejected"]},
    )
    assert st == "no_fit"
    assert any("candidate_doc_status_blocked" in x for x in rs)


def test_ok_status_fits():
    ok = next(iter(DEFAULT_CANDIDATE_DOCUMENT_OK_STATUSES))
    st, rs = evaluate_lead_criteria_v1(
        {},
        {"requires_candidate_documents_v1": ["driver_license"]},
        candidate_document_statuses={"driver_license": [ok]},
    )
    assert st == "fit"
    assert rs == []


def test_allowed_geo_countries_fit():
    st, rs = evaluate_lead_criteria_v1(
        {"geo_country": "DE", "country": "PL"},
        {"allowed_geo_countries": ["DE"]},
    )
    assert st == "fit"
    assert rs == []


def test_allowed_geo_countries_needs_info_without_geo():
    st, rs = evaluate_lead_criteria_v1(
        {"country": "PL"},
        {"allowed_geo_countries": ["DE"]},
    )
    assert st == "needs_info"
    assert "missing_geo_country" in rs


def test_allowed_geo_countries_alternate_keys():
    st, rs = evaluate_lead_criteria_v1(
        {"location_country": "NL"},
        {"allowed_geo_countries": ["NL"]},
    )
    assert st == "fit"


def test_blocked_geo_countries():
    st, rs = evaluate_lead_criteria_v1(
        {"current_country": "BY"},
        {"blocked_geo_countries": ["BY"]},
    )
    assert st == "no_fit"
    assert any(x.startswith("geo_country_blocked:") for x in rs)


def test_custom_allow_list():
    st, rs = evaluate_lead_criteria_v1(
        {},
        {
            "requires_candidate_documents_v1": ["passport"],
            "candidate_documents_allow_statuses": ["uploaded"],
        },
        candidate_document_statuses={"passport": ["uploaded"]},
    )
    assert st == "fit"
    assert rs == []


@pytest.mark.asyncio
async def test_batch_loader_smoke():
    from backend.app.modules.leads.lead_candidate_doc_loader import batch_candidate_document_status_sets

    class _FakeResult:
        def all(self):
            return []

    class _FakeDb:
        async def execute(self, _stmt):
            return _FakeResult()

    out = await batch_candidate_document_status_sets(
        _FakeDb(),  # type: ignore[arg-type]
        tenant_id="t1",
        candidate_ids={"c1", "c2"},
    )
    assert set(out.keys()) == {"c1", "c2"}
    assert out["c1"] == {}


def test_lead_fit_evaluation_effective_explicit_off_ignores_criteria():
    extra = {"lead_fit_evaluation_enabled_v1": False, "lead_criteria_v1": {"min_experience_eu_years": 5}}
    assert lead_fit_evaluation_effective(extra) is False
    st, rs = evaluate_vacancy_for_lead({"experience_eu_years": 0}, extra)
    assert st == "no_criteria"
    assert rs == []


def test_lead_fit_evaluation_effective_explicit_on_empty_criteria():
    extra = {"lead_fit_evaluation_enabled_v1": True, "lead_criteria_v1": {}}
    assert lead_fit_evaluation_effective(extra) is True
    st, _ = evaluate_vacancy_for_lead({}, extra)
    assert st == "no_criteria"


def test_lead_fit_evaluation_effective_legacy_nonempty_criteria():
    extra = {"lead_criteria_v1": {"min_experience_eu_years": 3}}
    assert lead_fit_evaluation_effective(extra) is True
    st, rs = evaluate_vacancy_for_lead({"experience_eu_years": 1}, extra)
    assert st == "no_fit"
    assert rs
