"""HE-4 Hiring E2E Acceptance walk (RS-7).

One candidate on product HTTP surfaces: operator policy, stage moves,
a required request taken from the outstanding set, candidate provision,
direct operator upload of the other outstanding documents, Document Link
and Candidate Evidence, readable refusal while an RPM requirement is unmet,
then transfer. An ad-hoc request outside the set does not become a requirement.

Inadmissible and not used: ``seed_documents_for_ready_for_handoff``,
``candidate_evidence_helpers``, SQL/fixture inserts, ``GET /transfer-readiness``.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from backend.app.db.session import async_session_maker
from backend.app.reference.hiring_eligibility_composition import requirement_refusal

pytestmark = pytest.mark.anyio

_REQUIRED_CODE = "adr_certificate"
_OUTSIDER_CODE = "visa"
_OPERATOR_DELTA = {
    "vacancy": {"additions": [{"when": {}, "require": [_REQUIRED_CODE]}]},
}


def _extraction_meta(code: str) -> dict[str, Any]:
    """Fields the operator records for this type's required metadata schema."""
    issued = "2024-01-15"
    expires = "2029-01-15"
    meta: dict[str, Any] = {
        "number": f"{code}-2024-001",
        "issued_at": issued,
        "expires_at": expires,
        "country": "PL",
        "issued_by": "PL",
    }
    if code == "adr_certificate":
        meta["classes"] = ["1"]
    if code == "driver_license":
        meta["categories"] = ["CE"]
    return meta


async def _outstanding(
    client: AsyncClient,
    headers: dict[str, str],
    candidate_id: str,
) -> dict[str, Any]:
    response = await client.get(
        f"/api/v1/candidates/{candidate_id}/requirements/outstanding",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, dict), body
    return body


async def _provide_requirement_document(
    client: AsyncClient,
    headers: dict[str, str],
    candidate_id: str,
    code: str,
) -> str:
    """Upload, Hub-approve, and record extraction metadata on the returned instance."""
    upload_headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
    meta = _extraction_meta(code)
    uploaded = await client.post(
        f"/api/v1/candidates/{candidate_id}/documents/upload",
        headers=upload_headers,
        data={"key": code, "title": code, "status": "uploaded"},
        files={"file": (f"{code}.txt", f"{code} scan".encode(), "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    document_id = str(uploaded.json()["id"])

    accepted = await client.patch(
        f"/api/v1/candidates/{candidate_id}/documents/{document_id}",
        headers=headers,
        json={"status": "approved"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json().get("status") == "approved"

    recorded = await client.patch(
        f"/api/v1/candidates/{candidate_id}/documents/{document_id}",
        headers=headers,
        json={
            "number": meta["number"],
            "issued_at": meta["issued_at"],
            "expires_at": meta["expires_at"],
            "meta": meta,
        },
    )
    assert recorded.status_code == 200, recorded.text
    return document_id


async def _bind_requirement_evidence(
    client: AsyncClient,
    headers: dict[str, str],
    manager_headers: dict[str, str],
    candidate_id: str,
    code: str,
    document_id: str,
) -> None:
    checklist = await client.get(
        f"/api/v1/candidates/{candidate_id}/requirements/checklist",
        headers=manager_headers,
    )
    assert checklist.status_code == 200, checklist.text
    body = checklist.json()
    rows = body.get("requirements") if isinstance(body, dict) else body
    if isinstance(body, dict) and not rows:
        rows = body.get("items") or body.get("checklist") or []
    target = None
    for row in rows or []:
        if str(row.get("requirement_code") or row.get("code") or "") == code:
            target = row
            break
    assert target is not None, checklist.text
    variants = target.get("accepted_evidence_variants") or [{}]
    variant = variants[0].get("evidence_variant_code") or code
    selected = await client.post(
        f"/api/v1/candidates/{candidate_id}/requirements/{code}/select-evidence",
        headers=headers,
        json={"evidence_variant_code": variant},
    )
    assert selected.status_code == 200, selected.text
    evidence_id = selected.json().get("evidence_id") or selected.json().get("id")
    assert evidence_id, selected.text

    linked = await client.post(
        f"/api/v1/candidates/{candidate_id}/requirements/evidence/{evidence_id}/documents",
        headers=headers,
        json={"document_id": document_id},
    )
    assert linked.status_code == 200, linked.text

    approved = await client.post(
        f"/api/v1/candidates/{candidate_id}/requirements/evidence/{evidence_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200, approved.text


def _detail(response) -> Any:
    try:
        body = response.json()
    except Exception:
        return response.text
    if isinstance(body, dict) and "detail" in body:
        return body["detail"]
    return body


async def _stage(client: AsyncClient, headers: dict[str, str], candidate_id: str, stage: str):
    return await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=headers,
        json={"stage": stage},
    )


@pytest.mark.anyio
async def test_documents_status_column_matches_orm() -> None:
    async with async_session_maker() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'documents'
                      AND column_name IN ('status', 'status_new')
                    """
                )
            )
        ).scalars().all()
    columns = set(rows)
    assert "status" in columns
    assert "status_new" not in columns


@pytest.mark.anyio
async def test_rs7_operator_surface_walk(client: AsyncClient, manager_headers: dict[str, str]) -> None:
    """Walk RS-7. A missing operator step fails the gate; it does not seed around it."""
    headers = {**manager_headers, "Content-Type": "application/json"}

    overlay = await client.put(
        "/api/v1/platform/document-policy-overlay",
        headers=headers,
        json={
            "tenant_delta": _OPERATOR_DELTA,
            "reason": "RS-7 walk requires adr_certificate before transfer",
        },
    )
    assert overlay.status_code == 200, overlay.text
    resolved = overlay.json().get("resolved_policy") or {}
    assert _REQUIRED_CODE in str(resolved).lower()

    company = await client.post(
        "/api/v1/companies/",
        headers=headers,
        json={"name": f"HE4 Walk {uuid.uuid4().hex[:8]}", "country": "PL"},
    )
    assert company.status_code == 200, company.text
    company_id = company.json()["id"]

    vacancy = await client.post(
        "/api/v1/vacancies/",
        headers=headers,
        json={"company_id": company_id, "title": "HE4 driver"},
    )
    assert vacancy.status_code == 200, vacancy.text
    vacancy_id = vacancy.json()["id"]

    clause = await client.post(
        "/api/v1/legal-documents/",
        headers=headers,
        json={
            "type": "rodo_clause",
            "version_id": f"he4-walk-{uuid.uuid4().hex[:8]}",
            "content_html": "<p>RODO notice for the hiring walk.</p>",
            "is_active": True,
        },
    )
    assert clause.status_code == 201, clause.text

    candidate_email = f"he4-{uuid.uuid4().hex[:8]}@example.com"
    created = await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={
            "first_name": "Helena",
            "last_name": "Walk",
            "email": candidate_email,
            "phone": "+48111222333",
            "stage": "new",
            "vacancy_id": vacancy_id,
        },
    )
    assert created.status_code == 200, created.text
    candidate_id = created.json()["id"]
    tenant_id = created.json()["tenant_id"]
    assert created.json().get("stage") == "new"

    rodo_status = await client.get(
        f"/api/v1/legal-documents/candidates/{candidate_id}/rodo-status",
        headers=manager_headers,
    )
    assert rodo_status.status_code == 200, rodo_status.text
    if not rodo_status.json().get("sent"):
        rodo = await client.post(
            f"/api/v1/legal-documents/candidates/{candidate_id}/send-rodo",
            headers=headers,
        )
        assert rodo.status_code == 200, rodo.text

    for stage in ("contacted", "docs_wait"):
        moved = await _stage(client, headers, candidate_id, stage)
        assert moved.status_code == 200, moved.text
        assert moved.json().get("stage") == stage

    history = await client.get(
        f"/api/v1/candidates/{candidate_id}/stage-history",
        headers=manager_headers,
    )
    assert history.status_code == 200, history.text
    history_stages = {
        str(row.get("to_code") or row.get("to_stage") or row.get("stage") or "")
        for row in history.json()
    }
    assert "contacted" in history_stages or "docs_wait" in history_stages, history.text

    refused = await _stage(client, headers, candidate_id, "ready_for_handoff")
    assert refused.status_code == 409, refused.text
    refusal = _detail(refused)
    assert isinstance(refusal, dict), refusal
    assert refusal.get("requirement_conjunct_source") == "rpm_result", refusal
    unmet = [str(code) for code in (refusal.get("missing_types") or [])]
    assert _REQUIRED_CODE in unmet, refusal
    reason = str(refusal.get("refusal_reason") or refusal.get("message") or "")
    assert reason == requirement_refusal(tuple(sorted(set(unmet)))), refusal

    outstanding = await _outstanding(client, headers, candidate_id)
    outstanding_codes = [str(code) for code in outstanding.get("outstanding_codes") or []]
    assert set(outstanding_codes) == set(unmet), outstanding
    assert _REQUIRED_CODE in outstanding_codes
    assert _OUTSIDER_CODE not in outstanding_codes
    assert _OUTSIDER_CODE not in unmet

    # Vacancy-driven request refuses a type the policy does not have outstanding.
    outsider_request = await client.post(
        f"/api/v1/candidates/{candidate_id}/requirements/{_OUTSIDER_CODE}/request",
        headers=headers,
    )
    assert outsider_request.status_code == 409, outsider_request.text
    outsider_detail = _detail(outsider_request)
    assert isinstance(outsider_detail, dict), outsider_detail
    assert outsider_detail.get("code") == "not_outstanding_requirement", outsider_detail

    # A recruiter may still ask for that type. The ask stays ad-hoc and does
    # not enter the outstanding set or the eligibility refusal.
    ad_hoc = await client.post(
        f"/api/v1/candidates/{candidate_id}/documents",
        headers=headers,
        json={"doc_type": _OUTSIDER_CODE, "status": "requested", "title": _OUTSIDER_CODE},
    )
    assert ad_hoc.status_code == 201, ad_hoc.text
    assert ad_hoc.json().get("status") == "requested", ad_hoc.text
    assert (ad_hoc.json().get("meta") or {}).get("request_kind") == "ad_hoc", ad_hoc.text
    assert not (ad_hoc.json().get("meta") or {}).get("requirement_code"), ad_hoc.text

    still_outstanding = await _outstanding(client, headers, candidate_id)
    assert _OUTSIDER_CODE not in (still_outstanding.get("outstanding_codes") or [])
    assert set(still_outstanding.get("outstanding_codes") or []) == set(unmet)

    still_refused = await _stage(client, headers, candidate_id, "ready_for_handoff")
    assert still_refused.status_code == 409, still_refused.text
    still_detail = _detail(still_refused)
    assert isinstance(still_detail, dict), still_detail
    still_unmet = [str(code) for code in (still_detail.get("missing_types") or [])]
    assert _OUTSIDER_CODE not in still_unmet, still_detail
    assert _REQUIRED_CODE in still_unmet, still_detail

    required_request = await client.post(
        f"/api/v1/candidates/{candidate_id}/requirements/{_REQUIRED_CODE}/request",
        headers=headers,
    )
    assert required_request.status_code == 200, required_request.text
    required_body = required_request.json()
    assert required_body.get("request_kind") == "required", required_body
    assert required_body.get("requirement_code") == _REQUIRED_CODE, required_body
    assert required_body.get("status") == "requested", required_body
    candidate_link = str(required_body.get("candidate_link") or "")
    assert candidate_link.startswith("/public/status/"), required_body
    request_id = str(required_body["document_id"])
    share_token = candidate_link.rstrip("/").rsplit("/", 1)[-1]

    # The candidate provides the requested document on that same row.
    upload_headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
    provided_upload = await client.post(
        f"/api/v1/public/status/{share_token}/documents/upload",
        headers=upload_headers,
        data={"doc_type": _REQUIRED_CODE, "email": candidate_email},
        files={"file": (f"{_REQUIRED_CODE}.txt", f"{_REQUIRED_CODE} scan".encode(), "text/plain")},
    )
    assert provided_upload.status_code == 200, provided_upload.text

    listed = await client.get(
        f"/api/v1/candidates/{candidate_id}/documents",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    requested_row = next(
        (row for row in listed.json() if str(row.get("id")) == request_id),
        None,
    )
    assert requested_row is not None, listed.text
    assert requested_row.get("status") in {"submitted", "received", "uploaded"}, requested_row
    assert (requested_row.get("meta") or {}).get("request_kind") == "required", requested_row
    assert (requested_row.get("meta") or {}).get("requirement_code") == _REQUIRED_CODE

    accepted = await client.patch(
        f"/api/v1/candidates/{candidate_id}/documents/{request_id}",
        headers=headers,
        json={"status": "approved"},
    )
    assert accepted.status_code == 200, accepted.text
    adr_meta = _extraction_meta(_REQUIRED_CODE)
    recorded = await client.patch(
        f"/api/v1/candidates/{candidate_id}/documents/{request_id}",
        headers=headers,
        json={
            "number": adr_meta["number"],
            "issued_at": adr_meta["issued_at"],
            "expires_at": adr_meta["expires_at"],
            "meta": {**adr_meta, "request_kind": "required", "requirement_code": _REQUIRED_CODE},
        },
    )
    assert recorded.status_code == 200, recorded.text

    # The other outstanding documents are already in the operator's hands.
    # Providing them does not invent a request row.
    provided: dict[str, str] = {_REQUIRED_CODE: request_id}
    for code in sorted(set(outstanding_codes)):
        if code == _REQUIRED_CODE:
            continue
        provided[code] = await _provide_requirement_document(
            client, headers, candidate_id, code
        )

    resolved_docs = await client.get(
        "/api/v1/platform/documents/resolve",
        headers=manager_headers,
        params={
            "linked_entity_type": "candidate",
            "linked_entity_id": candidate_id,
            "relation_type": "primary",
        },
    )
    assert resolved_docs.status_code == 200, resolved_docs.text
    items = resolved_docs.json().get("items") or []
    resolved_ids = {str(item.get("id")) for item in items}
    assert set(provided.values()) <= resolved_ids, resolved_docs.text

    for code, document_id in provided.items():
        await _bind_requirement_evidence(
            client, headers, manager_headers, candidate_id, code, document_id
        )

    closed = await _outstanding(client, headers, candidate_id)
    still_open = set(closed.get("outstanding_codes") or [])
    assert still_open.isdisjoint(set(outstanding_codes)), closed
    assert _OUTSIDER_CODE not in still_open
    assert _REQUIRED_CODE in (closed.get("satisfied_codes") or []), closed

    transferred = await _stage(client, headers, candidate_id, "ready_for_handoff")
    if transferred.status_code == 409:
        detail = _detail(transferred)
        confirmations = detail.get("required_confirmations") if isinstance(detail, dict) else None
        # RPM is already eligible. The operator confirms each reviewed dossier
        # block on the same candidate PATCH the card uses, then retries transfer.
        if (
            isinstance(detail, dict)
            and detail.get("eligibility_status") == "eligible"
            and not detail.get("missing_types")
            and confirmations
        ):
            block_keys = [
                str(item.get("block_key")).strip()
                for item in confirmations
                if isinstance(item, dict) and str(item.get("block_key") or "").strip()
            ]
            confirmed = await client.patch(
                f"/api/v1/candidates/{candidate_id}",
                headers=headers,
                json={"extra": {"recruitment_dossier_confirmed_blocks": block_keys}},
            )
            assert confirmed.status_code == 200, confirmed.text
            transferred = await _stage(client, headers, candidate_id, "ready_for_handoff")
    assert transferred.status_code == 200, transferred.text
    assert transferred.json().get("stage") == "ready_for_handoff", transferred.text

    # Operator transfer: enable the employment destination on the client link,
    # then Передать на трудоустройство. The completion record is that response.
    links = await client.get(
        f"/api/v1/tenants/{tenant_id}/links",
        headers=manager_headers,
    )
    assert links.status_code == 200, links.text
    link = next(
        (
            row
            for row in links.json()
            if str(row.get("client_company_id") or "") == str(company_id)
        ),
        None,
    )
    assert link is not None, links.text
    enabled = await client.patch(
        f"/api/v1/tenants/{tenant_id}/links/{link['id']}",
        headers=headers,
        json={"handoff_to_internal_hr": True},
    )
    assert enabled.status_code == 200, enabled.text

    handoff = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers=headers,
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert handoff.status_code == 201, handoff.text
    assert "ready_for_employment.v1" in handoff.text, handoff.text
