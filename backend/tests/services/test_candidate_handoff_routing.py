from __future__ import annotations

from backend.app.services.candidate_handoff_routing import (
    CandidateHandoffRouteKind,
    resolve_candidate_handoff_route,
)


def test_direct_employer_to_hr_when_module_on() -> None:
    r = resolve_candidate_handoff_route(
        acting_company_business_type="direct_employer",
        agency_recruiting_for_client=False,
        client_has_hostflow_account=False,
        hr_module_enabled_for_receiver=True,
        client_portal_or_link_available=False,
    )
    assert r.kind == CandidateHandoffRouteKind.hr_module


def test_agency_client_hostflow_route() -> None:
    r = resolve_candidate_handoff_route(
        acting_company_business_type="agency",
        agency_recruiting_for_client=True,
        client_has_hostflow_account=True,
        hr_module_enabled_for_receiver=False,
        client_portal_or_link_available=True,
    )
    assert r.kind == CandidateHandoffRouteKind.client_hostflow


def test_agency_client_no_account_uses_portal_link() -> None:
    r = resolve_candidate_handoff_route(
        acting_company_business_type="agency",
        agency_recruiting_for_client=True,
        client_has_hostflow_account=False,
        hr_module_enabled_for_receiver=False,
        client_portal_or_link_available=True,
    )
    assert r.kind == CandidateHandoffRouteKind.client_portal_link
