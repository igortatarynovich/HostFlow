"""PR15 HR hybrid verification plan API E2E helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote

from httpx import AsyncClient

from backend.tests.api.test_handoff_internal_hr import (
    _ensure_tenant_link_internal_hr,
    internal_hr_handoff_create_and_accept,
)
from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff

BLOCKING_TIERS = frozenset({"hard_blocker", "required", "hr_requested"})


async def employee_id_for_candidate(
    client: AsyncClient, hr_headers: dict[str, str], candidate_id: str
) -> str:
    lst = await client.get("/api/v1/workforce/employees", headers=hr_headers)
    assert lst.status_code == 200, lst.text
    matches = [e for e in lst.json() if str(e.get("candidate_id") or "") == str(candidate_id)]
    assert len(matches) == 1
    return str(matches[0]["id"])


async def setup_hr_review_case(
    client: AsyncClient,
    *,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
    candidate_id: str,
    bootstrap: dict[str, Any],
    citizenship: str = "PL",
    position_category: Optional[str] = None,
) -> str:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    extra: dict[str, Any] = {"citizenship": citizenship}
    if position_category == "driver":
        extra["role"] = "driver"
    elif position_category:
        extra["position_category"] = position_category

    patch_cand = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers={**manager_headers, "Content-Type": "application/json"},
        json={"extra": extra},
    )
    assert patch_cand.status_code == 200, patch_cand.text

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )
    return await employee_id_for_candidate(client, hr_officer_headers, candidate_id)


async def fetch_hr_panel(
    client: AsyncClient, emp_id: str, hr_headers: dict[str, str]
) -> dict[str, Any]:
    r = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/hr-review",
        headers=hr_headers,
    )
    assert r.status_code == 200, r.text
    return r.json()


def plan_from_panel(panel: dict[str, Any]) -> dict[str, Any]:
    return panel.get("verification_plan") or {}


def iter_blocking_plan_docs(panel: dict[str, Any]) -> list[dict[str, Any]]:
    plan = plan_from_panel(panel)
    out: list[dict[str, Any]] = []
    for d in plan.get("documents") or []:
        if not isinstance(d, dict):
            continue
        if str(d.get("requirement_tier") or "") in BLOCKING_TIERS:
            out.append(d)
    return out


def _reviewed_fields_payload(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in doc.get("fields_to_review") or []:
        if not isinstance(f, dict):
            continue
        code = str(f.get("field_code") or "").strip()
        if not code:
            continue
        value = ""
        for v in (f.get("current_profile_values") or {}).values():
            if v is not None and str(v).strip():
                value = str(v).strip()
                break
        if not value:
            value = "E2E-CONFIRMED"
        out[code] = {"value": value, "comment": "", "confirmed": True}
    return out


async def verify_plan_document(
    client: AsyncClient,
    emp_id: str,
    hr_headers: dict[str, str],
    document_key: str,
    *,
    panel: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    panel = panel or await fetch_hr_panel(client, emp_id, hr_headers)
    doc = next(
        (d for d in (panel.get("documents_for_approval") or []) if d.get("document_key") == document_key),
        None,
    )
    assert doc and doc.get("document_id"), f"missing doc row for {document_key!r}"
    h = {**hr_headers, "Content-Type": "application/json"}
    path = (
        f"/api/v1/workforce/employees/{emp_id}/hr-review/document-verifications/"
        f"{quote(document_key, safe='')}/verify"
    )
    r = await client.post(path, headers=h, json={"reviewed_fields": _reviewed_fields_payload(doc)})
    assert r.status_code == 200, r.text
    return await fetch_hr_panel(client, emp_id, hr_headers)


async def confirm_all_blocking_documents(
    client: AsyncClient, emp_id: str, hr_headers: dict[str, str]
) -> dict[str, Any]:
    panel = await fetch_hr_panel(client, emp_id, hr_headers)
    for doc in iter_blocking_plan_docs(panel):
        key = str(doc.get("document_key") or "")
        if not key or not doc.get("document_id"):
            continue
        vs = str(doc.get("verification_status") or "").lower()
        if vs in ("verified", "not_required"):
            continue
        panel = await verify_plan_document(client, emp_id, hr_headers, key, panel=panel)
    return panel


async def fetch_handoff_hr_panel(
    client: AsyncClient, handoff_id: str, hr_headers: dict[str, str]
) -> dict[str, Any]:
    r = await client.get(
        f"/api/v1/handoffs/{handoff_id}/hr-review",
        headers=hr_headers,
    )
    assert r.status_code == 200, r.text
    return r.json()


async def verify_handoff_plan_document(
    client: AsyncClient,
    handoff_id: str,
    hr_headers: dict[str, str],
    document_key: str,
    *,
    panel: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    panel = panel or await fetch_handoff_hr_panel(client, handoff_id, hr_headers)
    doc = next(
        (d for d in (panel.get("documents_for_approval") or []) if d.get("document_key") == document_key),
        None,
    )
    assert doc and doc.get("document_id"), f"missing doc row for {document_key!r}"
    h = {**hr_headers, "Content-Type": "application/json"}
    path = (
        f"/api/v1/handoffs/{handoff_id}/hr-review/document-verifications/"
        f"{quote(document_key, safe='')}/verify"
    )
    r = await client.post(path, headers=h, json={"reviewed_fields": _reviewed_fields_payload(doc)})
    assert r.status_code == 200, r.text
    return await fetch_handoff_hr_panel(client, handoff_id, hr_headers)


async def confirm_all_blocking_handoff_documents(
    client: AsyncClient, handoff_id: str, hr_headers: dict[str, str]
) -> dict[str, Any]:
    panel = await fetch_handoff_hr_panel(client, handoff_id, hr_headers)
    for doc in iter_blocking_plan_docs(panel):
        key = str(doc.get("document_key") or "")
        if not key or not doc.get("document_id"):
            continue
        vs = str(doc.get("verification_status") or "").lower()
        if vs in ("verified", "not_required"):
            continue
        panel = await verify_handoff_plan_document(client, handoff_id, hr_headers, key, panel=panel)
    return panel


async def prepare_handoff_hr_review_for_approve(
    client: AsyncClient,
    handoff_id: str,
    hr_headers: dict[str, str],
) -> dict[str, Any]:
    from backend.app.services.hr_document_verification import VERIFICATION_GATED_CHECKLIST

    panel = await confirm_all_blocking_handoff_documents(client, handoff_id, hr_headers)
    for doc in iter_blocking_plan_docs(panel):
        key = str(doc.get("document_key") or "")
        vs = str(doc.get("verification_status") or "").lower()
        if not key or vs in ("verified", "not_required", "waived"):
            continue
        path = (
            f"/api/v1/handoffs/{handoff_id}/hr-review/document-verifications/"
            f"{quote(key, safe='')}/waive-requirement"
        )
        waived = await client.post(
            path,
            headers={**hr_headers, "Content-Type": "application/json"},
            json={"reason": "E2E — unblock delayed workforce approve"},
        )
        if waived.status_code == 200:
            panel = waived.json()

    for item in panel.get("checklist") or []:
        code = item.get("item_code")
        if not code or code in VERIFICATION_GATED_CHECKLIST:
            continue
        if str(item.get("status") or "").lower() in ("satisfied", "verified", "complete"):
            continue
        patch = await client.patch(
            f"/api/v1/handoffs/{handoff_id}/hr-review/checklist/{code}",
            headers={**hr_headers, "Content-Type": "application/json"},
            json={"satisfied": True},
        )
        if patch.status_code == 200:
            panel = patch.json()
    return panel
