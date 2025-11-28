import pytest


@pytest.mark.anyio
async def test_declined_stage_requires_reason(client, manager_headers):
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Test", "last_name": "Candidate"},
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]

    # reason is mandatory
    resp = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "declined"},
    )
    assert resp.status_code == 422

    # invalid reason code rejected
    resp = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "declined", "status_reason": ["unknown_code"]},
    )
    assert resp.status_code == 422

    # valid list accepted
    resp = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "declined", "status_reason": ["schedule", "salary"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stage"] == "declined"
    assert body["status_reason"] == ["schedule", "salary"]

    get_resp = await client.get(f"/api/v1/candidates/{candidate_id}", headers=manager_headers)
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["stage"] == "declined"
    assert fetched["status_reason"] == ["schedule", "salary"]


@pytest.mark.anyio
async def test_bulk_stage_requires_reason(client, manager_headers):
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Bulk", "last_name": "Candidate"},
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]

    resp = await client.post(
        "/api/v1/candidates/bulk-stage",
        headers=manager_headers,
        json={"candidate_ids": [candidate_id], "stage": "declined"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload[0]["ok"] is False
    assert "причин" in payload[0]["error"].lower()

    resp_ok = await client.post(
        "/api/v1/candidates/bulk-stage",
        headers=manager_headers,
        json={"candidate_ids": [candidate_id], "stage": "declined", "status_reason": ["schedule"]},
    )
    assert resp_ok.status_code == 200, resp_ok.text
    success_payload = resp_ok.json()
    assert success_payload[0]["ok"] is True
    assert success_payload[0]["stage"] == "declined"

    fetched = await client.get(f"/api/v1/candidates/{candidate_id}", headers=manager_headers)
    assert fetched.status_code == 200
    data = fetched.json()
    assert data["stage"] == "declined"
    assert data["status_reason"] == ["schedule"]

    history_resp = await client.get(
        f"/api/v1/candidates/{candidate_id}/stage-history",
        headers=manager_headers,
    )
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert history
    assert history[-1]["to_code"] == "declined"
    assert "Не подходит график работы" in (history[-1]["reason"] or "")


@pytest.mark.anyio
async def test_candidates_filter_by_status_reason(client, manager_headers):
    # candidate 1 with awaiting_residence
    resp1 = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Anna", "last_name": "Awaiting"},
    )
    assert resp1.status_code == 200, resp1.text
    cid1 = resp1.json()["id"]
    patch1 = await client.patch(
        f"/api/v1/candidates/{cid1}",
        headers=manager_headers,
        json={"stage": "rejected", "status_reason": ["awaiting_residence"]},
    )
    assert patch1.status_code == 200, patch1.text

    # candidate 2 with salary
    resp2 = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Boris", "last_name": "Declined"},
    )
    assert resp2.status_code == 200, resp2.text
    cid2 = resp2.json()["id"]
    patch2 = await client.patch(
        f"/api/v1/candidates/{cid2}",
        headers=manager_headers,
        json={"stage": "declined", "status_reason": ["salary"]},
    )
    assert patch2.status_code == 200, patch2.text

    resp_single = await client.get(
        "/api/v1/candidates",
        headers=manager_headers,
        params={"status_reason": "awaiting_residence"},
    )
    assert resp_single.status_code == 200, resp_single.text
    body_single = resp_single.json()
    assert body_single["total"] >= 1
    ids_single = {item["id"] for item in body_single["items"]}
    assert cid1 in ids_single
    assert cid2 not in ids_single

    resp_multi = await client.get(
        "/api/v1/candidates",
        headers=manager_headers,
        params=[("status_reason", "awaiting_residence"), ("status_reason", "salary")],
    )
    assert resp_multi.status_code == 200, resp_multi.text
    body_multi = resp_multi.json()
    ids_multi = {item["id"] for item in body_multi["items"]}
    assert cid1 in ids_multi
    assert cid2 in ids_multi
