"""Bulk and service-layer guards: recruitment lock (application_handed_off / handoff) cannot be bypassed."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import text

from backend.app.api.v1.candidates import service as cand_service
from backend.app.db.session import async_session_maker
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.services.recruitment_handoff_write_guard import AgencyRecruitmentWriteBypass
from backend.tests.conftest import _set_tenant


@pytest.mark.asyncio
async def test_bulk_stage_row_fails_when_application_handed_off(
    client: AsyncClient,
    manager_headers: dict,
    bootstrap: dict,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    recruiter_id = bootstrap["recruiter_id"]
    mgr_json = {**manager_headers, "Content-Type": "application/json"}

    cresp = await client.post(
        "/api/v1/candidates",
        headers=mgr_json,
        json={"first_name": "Bulk", "last_name": "LockStage"},
    )
    assert cresp.status_code == 200, cresp.text
    cid = cresp.json()["id"]

    app_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=cid,
                    status="handed_off",
                    recruiter_id=recruiter_id,
                )
            )
            await session.commit()

        resp = await client.post(
            "/api/v1/candidates/bulk-stage",
            headers=mgr_json,
            json={"candidate_ids": [cid], "stage": "contacted"},
        )
        assert resp.status_code == 200, resp.text
        row = resp.json()[0]
        assert row.get("ok") is False
        assert "Recruitment locked" in (row.get("error") or "")
        assert "application_handed_off" in (row.get("error") or "")
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(text("DELETE FROM recruitment_applications WHERE id = :id"), {"id": app_id})
            await session.commit()


@pytest.mark.asyncio
async def test_bulk_manager_row_fails_when_application_handed_off(
    client: AsyncClient,
    manager_headers: dict,
    bootstrap: dict,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    recruiter_id = bootstrap["recruiter_id"]
    supervisor_id = bootstrap["supervisor_id"]
    mgr_json = {**manager_headers, "Content-Type": "application/json"}

    cresp = await client.post(
        "/api/v1/candidates",
        headers=mgr_json,
        json={"first_name": "Bulk", "last_name": "LockMgr"},
    )
    assert cresp.status_code == 200, cresp.text
    cid = cresp.json()["id"]

    app_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=cid,
                    status="handed_off",
                    recruiter_id=recruiter_id,
                )
            )
            await session.commit()

        resp = await client.post(
            "/api/v1/candidates/bulk-manager",
            headers=mgr_json,
            json={"candidate_ids": [cid], "manager_id": supervisor_id},
        )
        assert resp.status_code == 200, resp.text
        row = resp.json()[0]
        assert row.get("ok") is False
        assert "Recruitment locked" in (row.get("error") or "")
        assert "cannot reassign manager" in (row.get("error") or "")
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(text("DELETE FROM recruitment_applications WHERE id = :id"), {"id": app_id})
            await session.commit()


@pytest.mark.asyncio
async def test_bulk_delete_row_fails_when_application_handed_off(
    client: AsyncClient,
    manager_headers: dict,
    bootstrap: dict,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    recruiter_id = bootstrap["recruiter_id"]
    mgr_json = {**manager_headers, "Content-Type": "application/json"}

    cresp = await client.post(
        "/api/v1/candidates",
        headers=mgr_json,
        json={"first_name": "Bulk", "last_name": "LockDel"},
    )
    assert cresp.status_code == 200, cresp.text
    cid = cresp.json()["id"]

    app_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=cid,
                    status="handed_off",
                    recruiter_id=recruiter_id,
                )
            )
            await session.commit()

        resp = await client.post(
            "/api/v1/candidates/bulk-delete",
            headers=mgr_json,
            json={"candidate_ids": [cid]},
        )
        assert resp.status_code == 200, resp.text
        row = resp.json()[0]
        assert row.get("ok") is False
        assert "Recruitment locked" in (row.get("error") or "")
        assert "cannot delete candidate" in (row.get("error") or "")
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(text("DELETE FROM recruitment_applications WHERE id = :id"), {"id": app_id})
            await session.commit()


@pytest.mark.asyncio
async def test_update_candidate_full_raises_when_locked_without_bypass(
    candidate_id: str,
    bootstrap: dict,
) -> None:
    """Direct service call (simulates import/worker) must not skip recruitment lock."""
    tenant_id = bootstrap["tenant_id"]
    recruiter_id = bootstrap["recruiter_id"]
    app_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    status="handed_off",
                    recruiter_id=recruiter_id,
                )
            )
            await session.commit()

        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            with pytest.raises(HTTPException) as ei:
                await cand_service.update_candidate_full(
                    session,
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    payload={"note": "worker attempt"},
                    actor_id=recruiter_id,
                    agency_recruitment_bypass=None,
                )
            assert ei.value.status_code == 403
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(text("DELETE FROM recruitment_applications WHERE id = :id"), {"id": app_id})
            await session.commit()


@pytest.mark.asyncio
async def test_update_candidate_full_allows_locked_when_valid_bypass(
    candidate_id: str,
    bootstrap: dict,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    recruiter_id = bootstrap["recruiter_id"]
    admin_id = bootstrap["admin_id"]
    app_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    status="handed_off",
                    recruiter_id=recruiter_id,
                )
            )
            await session.commit()

        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await cand_service.update_candidate_full(
                session,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                payload={"note": "admin correction under lock"},
                actor_id=admin_id,
                agency_recruitment_bypass=AgencyRecruitmentWriteBypass(
                    actor_role="administrator",
                    override_reason="integration — explicit bypass",
                ),
            )
            await session.commit()
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(text("DELETE FROM recruitment_applications WHERE id = :id"), {"id": app_id})
            await session.commit()


@pytest.mark.asyncio
async def test_create_contact_attempt_forbidden_when_application_handed_off(
    client: AsyncClient,
    manager_headers: dict,
    bootstrap: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    recruiter_id = bootstrap["recruiter_id"]
    candidate_id = bootstrap["candidate_id"]
    mgr_json = {**manager_headers, "Content-Type": "application/json"}

    async def _policy_on(*_a, **_k):
        return {
            "enabled": True,
            "max_attempts": 5,
            "post_action": "auto_reject",
            "stage_code": None,
            "rodo_sent": True,
            "tracking_disabled_reason": None,
        }

    async def _rodo_ok(*_a, **_k):
        return object()

    monkeypatch.setattr(
        "backend.app.services.contact_attempts.get_effective_contact_policy",
        _policy_on,
    )
    monkeypatch.setattr(
        "backend.app.services.contact_attempts.get_first_rodo_sent",
        _rodo_ok,
    )

    app_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    status="handed_off",
                    recruiter_id=recruiter_id,
                )
            )
            await session.commit()

        resp = await client.post(
            f"/api/v1/candidates/{candidate_id}/contact-attempts",
            headers=mgr_json,
            json={"channel": "call", "result": "no_answer"},
        )
        assert resp.status_code == 403, resp.text
        assert "Recruitment locked" in (resp.json().get("detail") or "")
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(text("DELETE FROM recruitment_applications WHERE id = :id"), {"id": app_id})
            await session.commit()


@pytest.mark.asyncio
async def test_vacancy_attach_candidate_forbidden_when_application_handed_off(
    client: AsyncClient,
    manager_headers: dict,
    bootstrap: dict,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    recruiter_id = bootstrap["recruiter_id"]
    candidate_id = bootstrap["candidate_id"]
    company_id = bootstrap["company_id"]
    mgr_json = {**manager_headers, "Content-Type": "application/json"}

    vac_resp = await client.post(
        "/api/v1/vacancies",
        headers=mgr_json,
        json={"title": "LockAttachVac", "company_id": company_id, "status": "open"},
    )
    assert vac_resp.status_code == 200, vac_resp.text
    vacancy_id = vac_resp.json()["id"]

    app_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    status="handed_off",
                    recruiter_id=recruiter_id,
                )
            )
            await session.commit()

        resp = await client.post(
            f"/api/v1/vacancies/{vacancy_id}/candidates",
            headers=mgr_json,
            json={"candidate_id": candidate_id},
        )
        assert resp.status_code == 403, resp.text
        assert "Recruitment locked" in (resp.json().get("detail") or "")
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(text("DELETE FROM recruitment_applications WHERE id = :id"), {"id": app_id})
            await session.commit()


@pytest.mark.asyncio
async def test_candidate_links_patch_forbidden_when_application_handed_off(
    client: AsyncClient,
    manager_headers: dict,
    bootstrap: dict,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    recruiter_id = bootstrap["recruiter_id"]
    candidate_id = bootstrap["candidate_id"]
    company_id = bootstrap["company_id"]
    mgr_json = {**manager_headers, "Content-Type": "application/json"}

    app_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    status="handed_off",
                    recruiter_id=recruiter_id,
                )
            )
            await session.commit()

        resp = await client.patch(
            f"/api/v1/candidate-links/{candidate_id}",
            headers=mgr_json,
            json={"company_id": company_id},
        )
        assert resp.status_code == 403, resp.text
        assert "Recruitment locked" in (resp.json().get("detail") or "")
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(text("DELETE FROM recruitment_applications WHERE id = :id"), {"id": app_id})
            await session.commit()
