"""PATCH after create: initial fill must not require override_reason (regression)."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_get_candidate_empty_scope_tenant_id_query_ok(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    """``?scope_tenant_id=`` must not 422 (FastAPI UUID parser rejects empty string)."""
    r = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        params={"scope_tenant_id": ""},
    )
    assert r.status_code == 200, r.text


async def test_patch_personal_fields_after_minimal_create_without_override_ok(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    """Frontend POSTs CREATE_FIELDS only, then PATCHes address/country/extra — must not 422."""
    rid = bootstrap["recruiter_id"]
    cid = bootstrap["company_id"]
    r = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={
            "first_name": "Partial",
            "last_name": "Create",
            "email": "partial.create@example.com",
            "stage": "new",
            "manager_id": rid,
            "company_id": cid,
        },
    )
    assert r.status_code == 200, r.text
    new_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/candidates/{new_id}",
        headers=manager_headers,
        json={
            "country_code": "PL",
            "city": "Warsaw",
            "birth_date": "1990-01-15",
            "address": {"country": "PL", "city": "Warsaw", "street": "Marszałkowska", "house": "1"},
            "extra": {"current_location": "in_poland", "poland_stay_basis": "visa_c"},
            "note": "hello",
        },
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body.get("country_code") == "PL" or (body.get("personal_data") or {}).get("country_code") == "PL"


async def test_patch_changes_existing_candidate_owned_field_without_override_422(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    rid = bootstrap["recruiter_id"]
    cid = bootstrap["company_id"]
    r = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={
            "first_name": "Has",
            "last_name": "Country",
            "email": "has.country@example.com",
            "stage": "new",
            "manager_id": rid,
            "company_id": cid,
            "country_code": "PL",
        },
    )
    assert r.status_code == 200, r.text
    new_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/candidates/{new_id}",
        headers=manager_headers,
        json={"country_code": "DE"},
    )
    assert r2.status_code == 422, r2.text
    detail = r2.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "override_reason_required"
