"""HTTP persist + D4 resolve proof for RPM-2 operator overlay."""

from __future__ import annotations

PROOF_DELTA = {
    "vacancy": {
        "additions": [{"when": {}, "require": ["adr_certificate"]}],
    }
}
PROOF_REASON = "Require ADR certificate for this tenant overlay proof."


async def test_overlay_get_shape_is_merge_not_sample(client, manager_headers):
    response = await client.get(
        "/api/v1/platform/document-policy-overlay",
        headers=manager_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "sample" not in body
    assert "sample_evaluation" not in body
    assert isinstance(body.get("tenant_delta"), dict)
    assert "resolved_policy" in body
    assert "reason" in body
    assert body["resolved_policy"]["candidate"]["defaults"]["requiredTypes"]
    assert "adr_certificate" in body["resolved_policy"]["candidate"]["defaults"]["optionalTypes"]


async def test_overlay_get_forbidden_for_viewer(client, viewer_headers):
    response = await client.get(
        "/api/v1/platform/document-policy-overlay",
        headers=viewer_headers,
    )
    assert response.status_code == 403, response.text


async def test_overlay_put_rejects_reason_inside_delta(client, manager_headers):
    response = await client.put(
        "/api/v1/platform/document-policy-overlay",
        headers=manager_headers,
        json={
            "tenant_delta": {"reason": "no", "vacancy": {"additions": []}},
            "reason": PROOF_REASON,
        },
    )
    assert response.status_code == 422, response.text


async def test_overlay_put_persists_delta_and_changes_d4_applicability(
    client, manager_headers, candidate_id
):
    reset = await client.put(
        "/api/v1/platform/document-policy-overlay",
        headers=manager_headers,
        json={"tenant_delta": {}, "reason": "Reset overlay before RPM-2 proof."},
    )
    assert reset.status_code == 200, reset.text

    before = await client.get(
        "/api/v1/platform/documents/resolve",
        headers=manager_headers,
        params={
            "linked_entity_type": "candidate",
            "linked_entity_id": candidate_id,
            "relation_type": "primary",
        },
    )
    assert before.status_code == 200, before.text
    before_required = {
        row["doc_type"]
        for row in before.json().get("applicability") or []
        if row.get("applicability") == "required"
    }
    assert "adr_certificate" not in before_required

    put = await client.put(
        "/api/v1/platform/document-policy-overlay",
        headers=manager_headers,
        json={"tenant_delta": PROOF_DELTA, "reason": PROOF_REASON},
    )
    assert put.status_code == 200, put.text
    overlay = put.json()
    assert overlay["tenant_delta"] == PROOF_DELTA
    assert overlay["reason"] == PROOF_REASON
    assert "reason" not in overlay["tenant_delta"]
    additions = overlay["resolved_policy"]["vacancy"]["additions"]
    assert any("adr_certificate" in (rule.get("require") or []) for rule in additions)

    got = await client.get(
        "/api/v1/platform/document-policy-overlay",
        headers=manager_headers,
    )
    assert got.status_code == 200, got.text
    assert got.json()["tenant_delta"] == PROOF_DELTA
    assert got.json()["reason"] == PROOF_REASON
    assert got.json()["resolved_policy"] == overlay["resolved_policy"]

    after = await client.get(
        "/api/v1/platform/documents/resolve",
        headers=manager_headers,
        params={
            "linked_entity_type": "candidate",
            "linked_entity_id": candidate_id,
            "relation_type": "primary",
        },
    )
    assert after.status_code == 200, after.text
    after_required = {
        row["doc_type"]
        for row in after.json().get("applicability") or []
        if row.get("applicability") == "required"
    }
    assert "adr_certificate" in after_required

    reset = await client.put(
        "/api/v1/platform/document-policy-overlay",
        headers=manager_headers,
        json={"tenant_delta": {}, "reason": "Reset overlay after RPM-2 proof."},
    )
    assert reset.status_code == 200, reset.text
