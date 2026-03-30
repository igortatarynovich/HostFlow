"""license_addon_v1: seat/portal extras vs plan base (§2.16 / billing sync)."""

from __future__ import annotations

from backend.app.api.v1.settings.billing import build_license_addon_v1_payload
from backend.app.models.tenant import TenantLicense


def _team_row(**overrides: int) -> TenantLicense:
    base = dict(
        tenant_id="t1",
        plan="team",
        max_recruiters=2,
        max_supervisors=1,
        max_client_managers=0,
        max_viewers=0,
        max_storage_gb=50,
        max_companies=1,
        max_candidates_active=2000,
        max_vacancies_active=50,
        max_documents=10000,
        max_public_portal_links=3,
    )
    base.update(overrides)
    return TenantLicense(**base)  # type: ignore[arg-type]


def test_build_license_addon_v1_extra_recruiters() -> None:
    row = _team_row(max_recruiters=5)
    assert build_license_addon_v1_payload("team", row) == {"max_recruiters_delta": 3}


def test_build_license_addon_v1_no_extras() -> None:
    row = _team_row()
    assert build_license_addon_v1_payload("team", row) == {}


def test_build_license_addon_v1_portal_links() -> None:
    row = _team_row(max_public_portal_links=10)
    assert build_license_addon_v1_payload("team", row) == {"max_public_portal_links_delta": 7}


def test_build_license_addon_v1_active_candidates_and_storage() -> None:
    row = _team_row(max_candidates_active=5000, max_storage_gb=80)
    assert build_license_addon_v1_payload("team", row) == {
        "max_candidates_active_delta": 3000,
        "max_storage_gb_delta": 30,
    }
