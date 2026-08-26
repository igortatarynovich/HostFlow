from __future__ import annotations

from types import SimpleNamespace

from backend.app.services.stage_meta_recruitment_filter import handoff_lane_active_for_company


def _link(*, company_id: str, enabled: bool, include_id: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        client_company_id=company_id,
        handoff_include_company_id=include_id,
        get_handoff_enabled=lambda enabled=enabled: enabled,
    )


def test_company_without_handoff_is_not_locked_by_sibling_client() -> None:
    poltrakt = "2b1ca966-e77d-4a45-9fa6-33ef4c7c2cd5"
    mrozek = "c17d9487-eedf-4333-aeb6-e446357ce570"
    links = [
        _link(company_id=poltrakt, enabled=False),
        _link(company_id=mrozek, enabled=True),
    ]
    assert handoff_lane_active_for_company(links, company_id=poltrakt) is False
    assert handoff_lane_active_for_company(links, company_id=mrozek) is True
    # Unscoped meta must not lock employment funnels for handoff-off clients.
    assert handoff_lane_active_for_company(links, company_id=None) is False


def test_unknown_company_does_not_inherit_tenant_handoff() -> None:
    links = [_link(company_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", enabled=True)]
    assert handoff_lane_active_for_company(links, company_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb") is False
