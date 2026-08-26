"""Internal HR handoff (agency workforce) vs client portal."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from backend.tests.conftest import DEFAULT_TENANT_ID, _init_data
from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff
from backend.tests.test_support.candidate_evidence_helpers import RECRUITMENT_DOSSIER_CONFIRMED_BLOCKS


async def _ensure_hr_employee_funnel_for_company(
    *,
    tenant_id: str,
    company_id: str,
) -> None:
    from sqlalchemy import select, text

    from backend.app.db.session import async_session_maker
    from backend.app.models.company import Company
    from backend.app.models.tenant import Tenant
    from backend.app.services.hr_employee_funnel_bootstrap import bootstrap_hr_employee_funnel_for_company

    async with async_session_maker() as session:
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )
        tenant = (await session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
        company = (await session.execute(select(Company).where(Company.id == company_id))).scalar_one()
        await bootstrap_hr_employee_funnel_for_company(db=session, tenant=tenant, company=company)
        await session.commit()


async def _ensure_tenant_link_internal_hr(
    client: AsyncClient,
    *,
    manager_headers: dict[str, str],
    tenant_id: str,
    company_id: str,
) -> None:
    lst = await client.get(
        f"/api/v1/tenants/{tenant_id}/links",
        headers=manager_headers,
    )
    assert lst.status_code == 200, lst.text
    for row in lst.json():
        if str(row.get("client_company_id") or "") == str(company_id):
            link_id = row["id"]
            patch = await client.patch(
                f"/api/v1/tenants/{tenant_id}/links/{link_id}",
                headers=manager_headers,
                json={
                    "handoff_enabled": True,
                    "handoff_to_client": True,
                    "handoff_to_internal_hr": True,
                },
            )
            assert patch.status_code == 200, patch.text
            return
    create = await client.post(
        f"/api/v1/tenants/{tenant_id}/links",
        headers=manager_headers,
        json={
            "client_company_id": company_id,
            "handoff_enabled": True,
            "handoff_to_client": True,
            "handoff_to_internal_hr": True,
        },
    )
    assert create.status_code == 201, create.text


async def internal_hr_handoff_create_and_accept(
    client: AsyncClient,
    *,
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
    candidate_id: str,
    company_id: str,
    tenant_id: str | None = None,
) -> str:
    """PR-5: materialize HR workforce only via internal HR handoff + accept."""
    tid = tenant_id or DEFAULT_TENANT_ID
    await _ensure_hr_employee_funnel_for_company(tenant_id=tid, company_id=company_id)
    confirm = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"extra": {"recruitment_dossier_confirmed_blocks": list(RECRUITMENT_DOSSIER_CONFIRMED_BLOCKS)}},
    )
    assert confirm.status_code == 200, confirm.text
    rf = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"stage": "ready_for_handoff"},
    )
    assert rf.status_code == 200, rf.text
    ho = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho.status_code == 201, ho.text
    hid = ho.json()["id"]
    acc = await client.post(
        f"/api/v1/handoffs/{hid}/accept",
        headers=hr_officer_headers,
    )
    assert acc.status_code == 200, acc.text
    return str(hid)


@pytest.mark.anyio
async def test_internal_hr_handoff_not_in_client_portal_default_list(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={
            "first_name": "IntHR",
            "last_name": f"T{tag}",
            "company_id": company_id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]

    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    patch_resp = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert patch_resp.status_code == 200, patch_resp.text

    ho = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho.status_code == 201, ho.text
    assert ho.json().get("destination") == "internal_hr"

    cand_after_create = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
    )
    assert cand_after_create.status_code == 200, cand_after_create.text
    assert cand_after_create.json().get("stage") == "ready_for_handoff"

    emps_before = await client.get("/api/v1/workforce/employees", headers=manager_headers)
    assert emps_before.status_code == 200, emps_before.text
    rows_before = [r for r in emps_before.json() if str(r.get("candidate_id") or "") == str(candidate_id)]
    assert len(rows_before) == 0, rows_before

    # Default client-portal filter must not list internal HR rows
    cli = await client.get(
        "/api/v1/handoffs/pending-with-candidates",
        headers=hr_officer_headers,
        params={"client_company_id": company_id},
    )
    assert cli.status_code == 200, cli.text
    ids_default = {item["handoff"]["id"] for item in cli.json()}
    assert ho.json()["id"] not in ids_default

    hrq = await client.get(
        "/api/v1/handoffs/pending-with-candidates",
        headers=hr_officer_headers,
        params={"client_company_id": company_id, "handoff_destination": "internal_hr"},
    )
    assert hrq.status_code == 200, hrq.text
    ids_hr = {item["handoff"]["id"] for item in hrq.json()}
    assert ho.json()["id"] in ids_hr

    acc = await client.post(
        f"/api/v1/handoffs/{ho.json()['id']}/accept",
        headers=hr_officer_headers,
    )
    assert acc.status_code == 200, acc.text

    emps = await client.get("/api/v1/workforce/employees", headers=manager_headers)
    assert emps.status_code == 200, emps.text
    rows = [r for r in emps.json() if str(r.get("candidate_id") or "") == str(candidate_id)]
    assert len(rows) == 1, rows
    assert rows[0].get("status") == "onboarding"
    meta = rows[0].get("meta") or {}
    assert meta.get("internal_hr_handoff_id") == ho.json()["id"]
    bundle = await client.get(
        f"/api/v1/workforce/employees/{rows[0]['id']}/hr-bundle",
        headers=manager_headers,
    )
    assert bundle.status_code == 200, bundle.text
    assert len(bundle.json().get("onboarding_tasks") or []) >= 1

    cand = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=hr_officer_headers,
    )
    assert cand.status_code == 200, cand.text
    assert cand.json().get("stage") == "processing_by_hr"


@pytest.mark.anyio
async def test_internal_hr_handoff_locks_recruiter_edit_hr_can_edit_and_checklist_tasks(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={
            "first_name": "Lock",
            "last_name": f"T{tag}",
            "company_id": company_id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]

    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    patch_stage = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert patch_stage.status_code == 200, patch_stage.text

    ho = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho.status_code == 201, ho.text

    due_to_pre = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    pend = await client.get(
        "/api/v1/activities",
        headers=hr_officer_headers,
        params={
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "type_filter": ["internal_hr_handoff_pending"],
            "assignee_scope": "team",
            "due_to": due_to_pre,
        },
    )
    assert pend.status_code == 200, pend.text
    pend_items = pend.json().get("items") or []
    assert len(pend_items) >= 1
    assert any(
        (i.get("payload") or {}).get("handoff_id") == ho.json()["id"] for i in pend_items
    )

    rec_get = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=recruiter_headers,
    )
    assert rec_get.status_code == 200, rec_get.text
    assert rec_get.json().get("can_edit") is False

    rec_patch = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=recruiter_headers,
        json={"note": "nope"},
    )
    assert rec_patch.status_code == 403, rec_patch.text

    hr_get = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=hr_officer_headers,
    )
    assert hr_get.status_code == 200, hr_get.text
    assert hr_get.json().get("can_edit") is True

    hr_patch = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=hr_officer_headers,
        json={"note": "hr ok"},
    )
    assert hr_patch.status_code == 200, hr_patch.text

    acc = await client.post(
        f"/api/v1/handoffs/{ho.json()['id']}/accept",
        headers=hr_officer_headers,
    )
    assert acc.status_code == 200, acc.text

    rec_doc = await client.post(
        f"/api/v1/candidates/{candidate_id}/documents",
        headers=recruiter_headers,
        json={"doc_type": "residence_card", "status": "pending"},
    )
    assert rec_doc.status_code == 403, rec_doc.text

    hr_doc = await client.post(
        f"/api/v1/candidates/{candidate_id}/documents",
        headers=hr_officer_headers,
        json={"doc_type": "residence_card", "status": "pending"},
    )
    assert hr_doc.status_code == 201, hr_doc.text

    due_to = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
    act = await client.get(
        "/api/v1/activities",
        headers=hr_officer_headers,
        params={
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "due_to": due_to,
        },
    )
    assert act.status_code == 200, act.text
    items = act.json().get("items") or []
    types = {str(i.get("type") or "") for i in items}
    assert "handoff_hr_checklist" in types
    keys = set()
    for i in items:
        pl = i.get("payload") or {}
        if isinstance(pl, dict) and pl.get("handoff_checklist_key"):
            keys.add(str(pl.get("handoff_checklist_key")))
    assert "verify_candidate_data" in keys
    assert "onboarding_checklist" in keys
    assert "documents_hr_review" in keys
    assert "zus_registration" in keys
    assert "medical_examination" in keys
    assert "psychological_assessment" in keys

    emps = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert emps.status_code == 200, emps.text
    wf_rows = [r for r in emps.json() if str(r.get("candidate_id") or "") == str(candidate_id)]
    assert len(wf_rows) == 1, emps.json()
    wf_ret = await client.post(
        f"/api/v1/workforce/employees/{wf_rows[0]['id']}/hr-review/return-to-recruitment",
        headers={**hr_officer_headers, "Content-Type": "application/json"},
        json={"reason": "needs recruiter fix"},
    )
    assert wf_ret.status_code == 200, wf_ret.text

    rec_get2 = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=recruiter_headers,
    )
    assert rec_get2.status_code == 200, rec_get2.text
    assert rec_get2.json().get("can_edit") is True


@pytest.mark.anyio
async def test_recruiter_can_reject_while_pending_internal_hr_handoff(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={
            "first_name": "Reject",
            "last_name": f"T{tag}",
            "company_id": company_id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]

    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    patch_stage = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert patch_stage.status_code == 200, patch_stage.text

    ho = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho.status_code == 201, ho.text

    rec_get = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=recruiter_headers,
    )
    assert rec_get.status_code == 200, rec_get.text
    assert rec_get.json().get("can_edit") is False
    perms = rec_get.json().get("permissions") or {}
    assert perms.get("can_close_recruitment") is True

    rec_reject = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=recruiter_headers,
        json={"stage": "rejected", "status_reason": ["language"]},
    )
    assert rec_reject.status_code == 200, rec_reject.text
    assert rec_reject.json().get("stage") == "rejected"


@pytest.mark.anyio
async def test_meta_stages_recruiter_handoff_filter_excludes_post_hr_codes(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    h_rec = {**recruiter_headers, "X-Tenant-Id": tenant_id}
    meta_unscoped = await client.get("/api/v1/meta/stages", headers=h_rec)
    assert meta_unscoped.status_code == 200, meta_unscoped.text
    assert meta_unscoped.json().get("recruiter_handoff_stage_filter") is None

    meta_r = await client.get(
        "/api/v1/meta/stages", headers=h_rec, params={"company_id": company_id}
    )
    assert meta_r.status_code == 200, meta_r.text
    body_r = meta_r.json()
    assert body_r.get("stage_visibility_mode") == "recruitment_handoff"
    assert body_r.get("recruiter_handoff_stage_filter") is True
    assert "processing_by_hr" not in (body_r.get("order") or [])
    assert "processing_by_client" not in (body_r.get("order") or [])
    assert "employed" not in (body_r.get("order") or [])
    assert "permit_received" not in (body_r.get("order") or [])
    assert "employment_pending" not in (body_r.get("order") or [])
    assert "hired" not in (body_r.get("order") or [])
    # ready_for_hr — финал Recruitment; не входит в RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES (может быть в воронке).
    assert "rejected" in (body_r.get("order") or [])
    assert "handoff_returned" in (body_r.get("order") or [])

    h_adm = {**manager_headers, "X-Tenant-Id": tenant_id}
    meta_a = await client.get("/api/v1/meta/stages", headers=h_adm)
    assert meta_a.status_code == 200, meta_a.text
    body_a = meta_a.json()
    assert body_a.get("recruiter_handoff_stage_filter") is None
    assert body_a.get("stage_visibility_mode") is None
    # Воронка в seed может не включать все системные post-handoff коды — важно, что фильтр не навешан.


@pytest.mark.anyio
async def test_meta_stages_hr_officer_internal_hr_lane(
    client: AsyncClient,
    manager_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    h_hr = {**hr_officer_headers, "X-Tenant-Id": tenant_id}
    meta_hr = await client.get(
        "/api/v1/meta/stages", headers=h_hr, params={"company_id": company_id}
    )
    assert meta_hr.status_code == 200, meta_hr.text
    body = meta_hr.json()
    assert body.get("stage_visibility_mode") == "internal_hr_handoff"
    assert "processing_by_hr" in (body.get("order") or [])
    assert "processing_by_client" not in (body.get("order") or [])


@pytest.mark.anyio
async def test_hr_internal_lane_patch_allowlist_after_accept(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    """HR may PATCH only hr_workforce slice on candidate; recruitment + identity are blocked."""
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "HRZ", "last_name": f"T{tag}", "company_id": company_id},
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )

    ok = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=hr_officer_headers,
        json={"note": "hr lane ok"},
    )
    assert ok.status_code == 200, ok.text

    rid = str(data["recruiter_id"])

    for forbidden_key, payload in [
        ("source", {"source": "referral"}),
        ("vacancy_id", {"vacancy_id": None}),
        ("recruiter_id", {"recruiter_id": rid}),
        ("stage", {"stage": "ready_for_handoff"}),
        ("status", {"status": "processing_by_hr"}),
        ("first_name", {"first_name": "Changed"}),
    ]:
        r = await client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=hr_officer_headers,
            json=payload,
        )
        assert r.status_code == 422, (forbidden_key, r.text)
        detail = r.json().get("detail")
        assert isinstance(detail, dict), r.text
        assert detail.get("code") == "hr_field_not_allowed", detail
        assert forbidden_key in (detail.get("fields") or []), detail
