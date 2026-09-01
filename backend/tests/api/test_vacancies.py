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


async def _archive_after_test(
    client: AsyncClient, headers: Dict[str, str], vacancy_id: str
) -> None:
    """Free the per-tenant ``open_vacancy`` quota slot the test consumed.

    Phase 2.6.D Stage D/G test guard — the default test tenant has a hard
    cap of 5 open vacancies; without an explicit teardown each test that
    ends with the row in ``status='open'`` blocks the next test in the
    file. Best-effort: failures here are swallowed so a real assert
    failure isn't masked by a teardown error.
    """
    try:
        await client.patch(
            f"/api/v1/vacancies/{vacancy_id}",
            headers=headers,
            json={"is_archived": True},
        )
    except Exception:
        pass


@pytest.mark.anyio
async def test_archive_flag_canonicalises_status_to_closed(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    """Phase 2.6.D Stage G — ``PATCH {is_archived: True}`` on an active row
    must persist canonical ``status='closed'`` (not the legacy literal
    ``'archived'``). Previously this hybrid (``is_archived=True &&
    status='open'`` or ``status='archived'``) confused NBA, list filters
    and ``vacancy_is_recruiting``; the invariant is now
    ``is_active = (status='open' AND NOT is_archived)``.
    """
    headers = _headers(manager_headers)
    company_id = await _first_company_id(client, headers)

    create_resp = await client.post(
        "/api/v1/vacancies",
        headers=headers,
        json={
            "company_id": company_id,
            "title": f"[auto] archive canonical {uuid.uuid4().hex[:6]}",
            "status": "open",
            "employment_type": "full_time",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    vacancy_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"is_archived": True},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    body = patch_resp.json()
    assert body.get("is_archived") is True
    assert body.get("status") == "closed", (
        f"Expected canonical 'closed' after archive, got {body.get('status')!r}"
    )
    assert body.get("is_active") is False


@pytest.mark.anyio
async def test_legacy_status_archived_alias_routes_to_closed_plus_is_archived(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    """Phase 2.6.D Stage G — old clients that still PATCH
    ``{status: "archived"}`` (not yet canonical) must still be honoured as
    "archive this", but the persisted row uses ``status='closed'`` +
    ``is_archived=True`` so downstream readers don't have to special-case
    a legacy literal forever.
    """
    headers = _headers(manager_headers)
    company_id = await _first_company_id(client, headers)

    create_resp = await client.post(
        "/api/v1/vacancies",
        headers=headers,
        json={
            "company_id": company_id,
            "title": f"[auto] archive legacy alias {uuid.uuid4().hex[:6]}",
            "status": "open",
            "employment_type": "full_time",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    vacancy_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"status": "archived"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    body = patch_resp.json()
    assert body.get("status") == "closed", (
        f"Legacy 'archived' alias must route to canonical 'closed', "
        f"got {body.get('status')!r}"
    )
    assert body.get("is_archived") is True
    assert body.get("is_active") is False


@pytest.mark.anyio
async def test_status_transition_open_to_filled_is_allowed(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    """Phase 2.6.D Stage D — ``open`` is the active hub; moving directly
    to any terminal (``filled``/``closed``/``cancelled``) is allowed
    without an interstitial reopen.
    """
    headers = _headers(manager_headers)
    company_id = await _first_company_id(client, headers)

    create_resp = await client.post(
        "/api/v1/vacancies",
        headers=headers,
        json={
            "company_id": company_id,
            "title": f"[auto] open->filled {uuid.uuid4().hex[:6]}",
            "status": "open",
            "employment_type": "full_time",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    vacancy_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"status": "filled"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json().get("status") == "filled"
    # `filled` is terminal and not 'open', so it doesn't consume a quota
    # slot — no teardown needed.


@pytest.mark.anyio
async def test_status_transition_closed_to_filled_is_blocked(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    """Phase 2.6.D Stage D — terminal-to-terminal moves require an
    explicit reopen first (``closed → open → filled``). Going directly
    would lose the "we restarted hiring" event from the audit trail.
    The router maps ``ValueError`` from the validator to HTTP 409
    Conflict (state conflict, not malformed input).
    """
    headers = _headers(manager_headers)
    company_id = await _first_company_id(client, headers)

    create_resp = await client.post(
        "/api/v1/vacancies",
        headers=headers,
        json={
            "company_id": company_id,
            "title": f"[auto] closed-blocked {uuid.uuid4().hex[:6]}",
            "status": "open",
            "employment_type": "full_time",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    vacancy_id = create_resp.json()["id"]

    close_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"status": "closed"},
    )
    assert close_resp.status_code == 200, close_resp.text
    assert close_resp.json().get("status") == "closed"

    blocked_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"status": "filled"},
    )
    assert blocked_resp.status_code == 409, blocked_resp.text
    detail = blocked_resp.json().get("detail", "")
    assert "closed" in detail and "filled" in detail, (
        f"Expected error message to mention both states, got: {detail!r}"
    )

    reopen_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"status": "open"},
    )
    assert reopen_resp.status_code == 200, reopen_resp.text
    assert reopen_resp.json().get("status") == "open"

    await _archive_after_test(client, headers, vacancy_id)


@pytest.mark.anyio
async def test_status_transition_on_hold_to_filled_is_blocked(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    """Phase 2.6.D Stage D — ``on_hold → filled`` is denied. Hiring while
    paused is a contradiction; the operator must reopen first
    (recorded as a state event) and then declare success.
    """
    headers = _headers(manager_headers)
    company_id = await _first_company_id(client, headers)

    create_resp = await client.post(
        "/api/v1/vacancies",
        headers=headers,
        json={
            "company_id": company_id,
            "title": f"[auto] hold-blocked {uuid.uuid4().hex[:6]}",
            "status": "open",
            "employment_type": "full_time",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    vacancy_id = create_resp.json()["id"]

    hold_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"status": "on_hold"},
    )
    assert hold_resp.status_code == 200, hold_resp.text
    assert hold_resp.json().get("status") == "on_hold"

    blocked_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"status": "filled"},
    )
    assert blocked_resp.status_code == 409, blocked_resp.text
    # Vacancy is on_hold (still counts as "non-open" for quota), so it
    # doesn't consume a quota slot. Belt-and-braces archive anyway.
    await _archive_after_test(client, headers, vacancy_id)


@pytest.mark.anyio
async def test_status_transition_legacy_paused_alias_normalises(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    """Phase 2.6.D Stage D + A — ``status='paused'`` from a legacy client
    is normalised to ``on_hold`` by the schema before reaching the
    transition validator, so the matrix sees ``open → on_hold`` (allowed)
    and the persisted row uses canonical ``on_hold``.
    """
    headers = _headers(manager_headers)
    company_id = await _first_company_id(client, headers)

    create_resp = await client.post(
        "/api/v1/vacancies",
        headers=headers,
        json={
            "company_id": company_id,
            "title": f"[auto] paused alias {uuid.uuid4().hex[:6]}",
            "status": "open",
            "employment_type": "full_time",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    vacancy_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=headers,
        json={"status": "paused"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json().get("status") == "on_hold", (
        f"Legacy 'paused' alias must canonicalise to 'on_hold', "
        f"got {patch_resp.json().get('status')!r}"
    )
    # `on_hold` doesn't consume the open-vacancy quota, but the create
    # call did briefly while the row was 'open'. Archive to keep the
    # tenant's quota footprint at 0 between tests.
    await _archive_after_test(client, headers, vacancy_id)


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


@pytest.mark.anyio
async def test_create_vacancy_unknown_company_is_not_500(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    headers = _headers(manager_headers)
    response = await client.post(
        "/api/v1/vacancies",
        headers=headers,
        json={
            "company_id": str(uuid.uuid4()),
            "title": f"[auto] missing company {uuid.uuid4().hex[:6]}",
            "status": "open",
            "employment_type": "full_time",
        },
    )
    assert response.status_code == 422, response.text
    assert "Company not found" in str(response.json().get("detail", ""))


@pytest.mark.anyio
async def test_create_vacancy_accepts_own_company_id(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    """Onboarding posts OwnCompany.id as company_id; that must not FK-500."""
    headers = _headers(manager_headers)
    own_resp = await client.get("/api/v1/own-companies", headers=headers)
    assert own_resp.status_code == 200, own_resp.text
    own_payload = own_resp.json()
    items = own_payload.get("items") if isinstance(own_payload, dict) else own_payload
    assert items, "Need an own company to exercise the remap"
    own_id = items[0]["id"]

    response = await client.post(
        "/api/v1/vacancies",
        headers=headers,
        json={
            "company_id": own_id,
            "title": f"[auto] own-company remap {uuid.uuid4().hex[:6]}",
            "status": "open",
            "employment_type": "full_time",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["company_id"] != own_id
    lookup = await client.get(f"/api/v1/vacancies/{body['id']}", headers=headers)
    assert lookup.status_code == 200, lookup.text
    await _archive_after_test(client, headers, body["id"])
