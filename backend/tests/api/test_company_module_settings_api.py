"""Company module settings API (ADR-005)."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_get_hr_module_settings_defaults(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["company_id"]
    r = await client.get(
        f"/api/v1/companies/{cid}/module-settings/hr",
        headers=manager_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["company_id"] == cid
    assert data["module_key"] == "hr"
    if not data["id"]:
        assert data["settings_json"] == {}
        assert data["is_enabled"] is False
    else:
        # Shared DB may have a legacy row; GET coerces HR JSON to HrModuleSettingsV1.
        assert data["settings_json"].get("version") == 1


async def test_patch_and_get_hr_settings(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["company_id"]
    p = await client.patch(
        f"/api/v1/companies/{cid}/module-settings/hr",
        headers=manager_headers,
        json={
            "settings_json": {
                "version": 1,
                "zus_checklist": [{"code": "nip", "label": "NIP", "required": True}],
            },
            "is_enabled": True,
        },
    )
    assert p.status_code == 200, p.text
    body = p.json()
    assert body["settings_json"]["version"] == 1
    assert body["settings_json"]["zus_checklist"][0]["code"] == "nip"
    assert body["is_enabled"] is True
    assert body["id"]
    assert body["configured_at"]

    g = await client.get(
        f"/api/v1/companies/{cid}/module-settings/hr",
        headers=manager_headers,
    )
    assert g.status_code == 200, g.text
    assert g.json()["settings_json"]["zus_checklist"][0]["code"] == "nip"


async def test_hr_officer_can_get_not_patch(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["company_id"]
    await client.patch(
        f"/api/v1/companies/{cid}/module-settings/hr",
        headers=manager_headers,
        json={"settings_json": {"version": 1, "hr_assignment_rules": {"default_queue": "ops"}}},
    )
    g = await client.get(
        f"/api/v1/companies/{cid}/module-settings/hr",
        headers=hr_officer_headers,
    )
    assert g.status_code == 200, g.text

    p = await client.patch(
        f"/api/v1/companies/{cid}/module-settings/hr",
        headers=hr_officer_headers,
        json={"is_enabled": False},
    )
    assert p.status_code == 403, p.text


async def test_recruiter_forbidden(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["company_id"]
    r = await client.get(
        f"/api/v1/companies/{cid}/module-settings/hr",
        headers=recruiter_headers,
    )
    assert r.status_code == 403, r.text


async def test_fleet_settings_unknown_field_422(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["company_id"]
    r = await client.patch(
        f"/api/v1/companies/{cid}/module-settings/fleet",
        headers=manager_headers,
        json={"settings_json": {"not_a_real_fleet_field": 1}},
    )
    assert r.status_code == 422, r.text


async def test_patch_and_get_fleet_settings(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["company_id"]
    p = await client.patch(
        f"/api/v1/companies/{cid}/module-settings/fleet",
        headers=manager_headers,
        json={
            "settings_json": {
                "version": 1,
                "vehicle_type_codes": ["tractor", "trailer"],
            },
            "is_enabled": True,
        },
    )
    assert p.status_code == 200, p.text
    body = p.json()
    assert body["settings_json"]["version"] == 1
    assert body["settings_json"]["vehicle_type_codes"] == ["tractor", "trailer"]
    assert body["is_enabled"] is True

    g = await client.get(
        f"/api/v1/companies/{cid}/module-settings/fleet",
        headers=manager_headers,
    )
    assert g.status_code == 200, g.text
    assert g.json()["settings_json"]["vehicle_type_codes"] == ["tractor", "trailer"]


async def test_hr_settings_unknown_field_422(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["company_id"]
    r = await client.patch(
        f"/api/v1/companies/{cid}/module-settings/hr",
        headers=manager_headers,
        json={"settings_json": {"not_a_real_hr_field": 1}},
    )
    assert r.status_code == 422, r.text


async def test_patch_recruitment_default_candidate_funnel(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["company_id"]

    create = await client.post(
        "/api/v1/funnels",
        headers=manager_headers,
        json={
            "company_id": cid,
            "type": "candidate",
            "name": "CMS Picker Pipeline",
            "is_default": True,
            "stages": [
                {
                    "code": "new",
                    "label": "New",
                    "system_stage": "new",
                    "order": 0,
                    "is_terminal": False,
                }
            ],
        },
    )
    assert create.status_code in (200, 201), create.text
    funnel_id = create.json()["id"]

    p = await client.patch(
        f"/api/v1/companies/{cid}/module-settings/recruitment",
        headers=manager_headers,
        json={
            "settings_json": {"version": 1, "default_candidate_funnel_id": funnel_id},
            "is_enabled": True,
        },
    )
    assert p.status_code == 200, p.text
    assert p.json()["settings_json"]["default_candidate_funnel_id"] == funnel_id

    g = await client.get(
        f"/api/v1/companies/{cid}/module-settings/recruitment",
        headers=manager_headers,
    )
    assert g.status_code == 200, g.text
    assert g.json()["settings_json"]["default_candidate_funnel_id"] == funnel_id


async def test_invalid_module_key_422(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["company_id"]
    r = await client.get(
        f"/api/v1/companies/{cid}/module-settings/not_a_module",
        headers=manager_headers,
    )
    assert r.status_code == 422, r.text


async def test_module_disabled_when_tenant_hr_off(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["company_id"]
    off = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": False},
    )
    assert off.status_code == 200, off.text
    try:
        r = await client.get(
            f"/api/v1/companies/{cid}/module-settings/hr",
            headers=manager_headers,
        )
        assert r.status_code == 403, r.text
    finally:
        on = await client.patch(
            "/api/v1/settings/team/modules",
            headers=manager_headers,
            json={"hr": True},
        )
        assert on.status_code == 200, on.text
