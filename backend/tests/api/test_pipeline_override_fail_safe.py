import pytest


@pytest.mark.anyio
async def test_pipeline_override_rejects_non_overridable_passport(client, recruiter_headers):
    """Fail-safe: identity / legal doc types cannot be waived (plan §12)."""
    create = await client.post(
        "/api/v1/candidates",
        headers=recruiter_headers,
        json={"first_name": "Waiver", "last_name": "FailSafe"},
    )
    assert create.status_code == 200, create.text
    cid = create.json()["id"]

    r = await client.post(
        f"/api/v1/candidates/{cid}/pipeline-overrides",
        headers=recruiter_headers,
        json={
            "doc_type_code": "passport",
            "reason": "Urgent hire exception requested by client",
            "requested_scope": "pipeline",
        },
    )
    assert r.status_code == 400, r.text
    assert r.json().get("detail") == "doc_type_not_overridable"


@pytest.mark.anyio
async def test_pipeline_override_accepts_waivable_driver_license(client, recruiter_headers):
    create = await client.post(
        "/api/v1/candidates",
        headers=recruiter_headers,
        json={"first_name": "Waiver", "last_name": "DriverOk"},
    )
    assert create.status_code == 200, create.text
    cid = create.json()["id"]

    r = await client.post(
        f"/api/v1/candidates/{cid}/pipeline-overrides",
        headers=recruiter_headers,
        json={
            "doc_type_code": "driver_license",
            "reason": "Client approved scan pending postal delivery",
            "requested_scope": "pipeline",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body.get("doc_type_code") == "driver_license"
    assert body.get("status") == "pending"
