import pytest


async def _create_candidate(client, headers) -> str:
    resp = await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"first_name": "Jan", "last_name": "Kowalski"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


@pytest.mark.anyio
async def test_candidate_employment_crud_flow(client, manager_headers):
    candidate_id = await _create_candidate(client, manager_headers)
    base_payload = {
        "employer_name": "Trans Logistics",
        "country": "pl",
        "position": "Driver CE",
        "start_date": "2024-01-01",
        "trailer_types": ["Tautliner", "  "],
        "route_types": ["PL-DE"],
        "eu_routes": True,
        "reason_for_leaving": "Relocation",
    }

    create_resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/employments",
        headers=manager_headers,
        json=base_payload,
    )
    assert create_resp.status_code == 201, create_resp.text
    employment = create_resp.json()
    assert employment["employer_name"] == "Trans Logistics"
    assert employment["country"] == "PL"
    assert employment["trailer_types"] == ["Tautliner"]
    assert employment["route_types"] == ["PL-DE"]
    assert employment["truck_brands"] is None

    list_resp = await client.get(
        f"/api/v1/candidates/{candidate_id}/employments",
        headers=manager_headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    invalid_update = await client.put(
        f"/api/v1/candidates/{candidate_id}/employments/{employment['id']}",
        headers=manager_headers,
        json={"end_date": "2023-12-31"},
    )
    assert invalid_update.status_code == 422

    update_resp = await client.put(
        f"/api/v1/candidates/{candidate_id}/employments/{employment['id']}",
        headers=manager_headers,
        json={
            "end_date": "2024-03-01",
            "truck_brands": ["Volvo", "  "],
            "reference_contact": "Hr Dept",
        },
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["end_date"] == "2024-03-01"
    assert updated["truck_brands"] == ["Volvo"]
    assert updated["reference_contact"] == "Hr Dept"

    delete_resp = await client.delete(
        f"/api/v1/candidates/{candidate_id}/employments/{employment['id']}",
        headers=manager_headers,
    )
    assert delete_resp.status_code == 204, delete_resp.text

    missing_delete = await client.delete(
        f"/api/v1/candidates/{candidate_id}/employments/{employment['id']}",
        headers=manager_headers,
    )
    assert missing_delete.status_code == 404


@pytest.mark.anyio
async def test_candidate_employment_limit_enforced(client, manager_headers):
    candidate_id = await _create_candidate(client, manager_headers)
    base_payload = {
        "employer_name": "Carrier",
        "position": "Driver",
        "start_date": "2024-01-01",
    }

    for idx in range(3):
        payload = dict(base_payload)
        payload["employer_name"] = f"Carrier {idx}"
        payload["start_date"] = f"2024-0{idx+1}-01"
        resp = await client.post(
            f"/api/v1/candidates/{candidate_id}/employments",
            headers=manager_headers,
            json=payload,
        )
        assert resp.status_code == 201, resp.text

    overflow = await client.post(
        f"/api/v1/candidates/{candidate_id}/employments",
        headers=manager_headers,
        json={**base_payload, "employer_name": "Overflow"},
    )
    assert overflow.status_code == 409
