import uuid
from typing import Any, Dict, List

import pytest
from httpx import AsyncClient

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"
EMPLOYMENT_TYPES = ("full_time", "part_time", "b2b")


def _headers(base: Dict[str, str]) -> Dict[str, str]:
    merged = dict(base)
    merged.setdefault("X-Tenant-Id", DEFAULT_TENANT_ID)
    merged.setdefault("Content-Type", "application/json")
    return merged


async def _first_company_id(client: AsyncClient, headers: Dict[str, str]) -> str:
    response = await client.get("/api/v1/companies?limit=1", headers=headers)
    response.raise_for_status()
    payload = response.json()

    items: List[Dict[str, Any]]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and "items" in payload and isinstance(payload["items"], list):
        items = payload["items"]
    else:
        raise AssertionError(f"Unexpected companies payload: {payload!r}")

    assert items, "Не найдено ни одной компании для создания вакансии"
    item = items[0]
    return item.get("id") or item.get("uuid") or item.get("company_id")


def _extract_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return items
        results = payload.get("results")
        if isinstance(results, list):
            return results
    raise AssertionError(f"Unexpected vacancies payload: {payload!r}")


@pytest.mark.anyio
@pytest.mark.parametrize("employment_type", EMPLOYMENT_TYPES)
async def test_create_vacancy_with_employment_type(
    client: AsyncClient, manager_headers: Dict[str, str], employment_type: str
) -> None:
    headers = _headers(manager_headers)
    company_id = await _first_company_id(client, headers)

    payload = {
        "company_id": company_id,
        "title": f"[auto] {employment_type} {uuid.uuid4().hex[:8]}",
        "status": "open",
        "employment_type": employment_type,
    }

    response = await client.post("/api/v1/vacancies", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    created = response.json()
    assert created["employment_type"] == employment_type

    # verify single GET
    lookup = await client.get(f"/api/v1/vacancies/{created['id']}", headers=headers)
    assert lookup.status_code == 200, lookup.text
    body = lookup.json()
    assert body["employment_type"] == employment_type


@pytest.mark.anyio
async def test_patch_updates_employment_type(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    headers = _headers(manager_headers)
    company_id = await _first_company_id(client, headers)

    create_payload = {
        "company_id": company_id,
        "title": f"[auto] employment patch {uuid.uuid4().hex[:6]}",
        "status": "open",
        "employment_type": "full_time",
    }
    created_resp = await client.post("/api/v1/vacancies", headers=headers, json=create_payload)
    assert created_resp.status_code == 200, created_resp.text
    vacancy_id = created_resp.json()["id"]

    patch_payload = {"employment_type": "b2b"}
    patched_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}", headers=headers, json=patch_payload
    )
    assert patched_resp.status_code == 200, patched_resp.text
    body = patched_resp.json()
    assert body["employment_type"] == "b2b"

    # list endpoint should reflect updated value
    list_resp = await client.get("/api/v1/vacancies", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    listings = list_resp.json()
    if isinstance(listings, dict) and "items" in listings:
        candidates = listings["items"]
    else:
        candidates = listings
    matched = next((item for item in candidates if item.get("id") == vacancy_id), None)
    assert matched is not None, "Созданная вакансия не найдена в списке"
    assert matched.get("employment_type") == "b2b"


@pytest.mark.anyio
async def test_invalid_employment_type_rejected(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    headers = _headers(manager_headers)
    company_id = await _first_company_id(client, headers)

    payload = {
        "company_id": company_id,
        "title": f"[auto] invalid employment {uuid.uuid4().hex[:6]}",
        "status": "open",
        "employment_type": "internship",
    }

    response = await client.post("/api/v1/vacancies", headers=headers, json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_archived_vacancies_listed_via_archived_filter(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    headers = _headers(manager_headers)
    company_id = await _first_company_id(client, headers)

    create_payload = {
        "company_id": company_id,
        "title": f"[auto] archive toggle {uuid.uuid4().hex[:6]}",
        "status": "open",
        "employment_type": "full_time",
    }
    create_resp = await client.post("/api/v1/vacancies", headers=headers, json=create_payload)
    assert create_resp.status_code == 200, create_resp.text
    vacancy_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"is_archived": True},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json().get("is_archived") is True

    default_list_resp = await client.get("/api/v1/vacancies", headers=headers)
    assert default_list_resp.status_code == 200, default_list_resp.text
    default_items = _extract_items(default_list_resp.json())
    assert all(item.get("id") != vacancy_id for item in default_items), "Archived vacancy leaked into default list"

    archived_list_resp = await client.get(
        "/api/v1/vacancies?status=archived",
        headers=headers,
    )
    assert archived_list_resp.status_code == 200, archived_list_resp.text
    archived_items = _extract_items(archived_list_resp.json())
    archived_entry = next((item for item in archived_items if item.get("id") == vacancy_id), None)
    assert archived_entry is not None, "Archived vacancy not present when requesting status=archived"
    assert archived_entry.get("is_archived") is True


@pytest.mark.anyio
async def test_patch_updates_company_id(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    headers = _headers(manager_headers)

    base_list = await client.get("/api/v1/companies?limit=2", headers=headers)
    base_list.raise_for_status()
    base_items = _extract_items(base_list.json())

    if len(base_items) < 2:
        create_resp = await client.post(
            "/api/v1/companies",
            headers=headers,
            json={"name": f"[auto] company {uuid.uuid4().hex[:6]}"},
        )
        assert create_resp.status_code == 200, create_resp.text
        base_items.append(create_resp.json())

    assert len(base_items) >= 2, "Need at least two companies to verify reassignment"
    company_a = base_items[0]["id"]
    company_b = base_items[1]["id"]

    create_payload = {
        "company_id": company_a,
        "title": f"[auto] company switch {uuid.uuid4().hex[:6]}",
        "status": "open",
        "employment_type": "full_time",
    }
    vacancy_resp = await client.post("/api/v1/vacancies", headers=headers, json=create_payload)
    assert vacancy_resp.status_code == 200, vacancy_resp.text
    vacancy_id = vacancy_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"company_id": company_b},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    body = patch_resp.json()
    assert body.get("company_id") == company_b

    lookup = await client.get(f"/api/v1/vacancies/{vacancy_id}", headers=headers)
    assert lookup.status_code == 200, lookup.text
    assert lookup.json().get("company_id") == company_b
