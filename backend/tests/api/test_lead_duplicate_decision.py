"""POST /leads/{id}/duplicate-decision — manual duplicate_review loop."""

from __future__ import annotations

import inspect
import json
import uuid

import pytest
from sqlalchemy import desc, func, select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead, RecruitmentApplication
from backend.app.models.audit import ActivityLog
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.modules.leads.service import _helpers
from backend.tests.api.lead_rodo_test_utils import satisfy_lead_rodo_via_source_for_tests
from backend.tests.api.test_leads_meta import (
    _ensure_company,
    _ensure_vacancy,
    _meta_payload,
    _signature_for_payload,
)
@pytest.mark.anyio
async def test_duplicate_decision_attach_existing(client, manager_headers, tenant_id) -> None:
    u = uuid.uuid4().hex[:10]
    hr_email = f"dd-attach-{u}@example.com"
    hr_phone = f"+48131{u[:8]}"

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        cand = Candidate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            first_name="Existing",
            last_name="Candidate",
            email=hr_email,
            stage="ready_for_hr",
            status="ready_for_hr",
            company_id=company_id,
        )
        session.add(cand)
        await session.flush()
        session.add(
            WorkforceEmployee(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=str(cand.id),
                display_name="DD Attach",
                status="onboarding",
            )
        )
        await session.commit()
        cand_id = cand.id
        vac_id = vacancy_id

    payload = _meta_payload(vac_id, email=hr_email, phone=hr_phone, lead_id=f"dd-attach-lg-{u}")
    post = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert post.status_code == 200, post.text
    lead_id = post.json()["lead_id"]
    assert post.json()["status"] == "duplicate_review"

    dec = await client.post(
        f"/api/v1/leads/{lead_id}/duplicate-decision",
        headers={**manager_headers, "Content-Type": "application/json"},
        json={"decision": "attach_existing", "note": "confirmed same person"},
    )
    assert dec.status_code == 200, dec.text
    body = dec.json()
    assert body["status"] == "duplicated"
    assert body["candidate_id"] == cand_id

    async with async_session_maker() as session:
        c2 = await session.get(Candidate, cand_id)
        assert c2 is not None
        origin = c2.origin if isinstance(c2.origin, dict) else {}
        intakes = origin.get("lead_duplicate_intakes_v1")
        assert isinstance(intakes, list) and any(x.get("lead_id") == lead_id for x in intakes)

        log_row = await session.execute(
            select(ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == "lead.duplicate_decision",
                ActivityLog.target_id == lead_id,
            )
            .order_by(desc(ActivityLog.created_at))
            .limit(1)
        )
        log_payload = log_row.scalar_one_or_none()
        assert isinstance(log_payload, dict)
        assert log_payload.get("decision") == "attach_existing"
        assert log_payload.get("candidate_id") == cand_id

        app_cnt = await session.execute(
            select(func.count())
            .select_from(RecruitmentApplication)
            .where(
                RecruitmentApplication.tenant_id == tenant_id,
                RecruitmentApplication.lead_id == lead_id,
            )
        )
        assert int(app_cnt.scalar_one() or 0) == 1


@pytest.mark.anyio
async def test_duplicate_decision_create_new_then_process(client, manager_headers, tenant_id) -> None:
    patch_settings = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": True, "leads_processing_mode_v1": "automatic"},
    )
    assert patch_settings.status_code == 200, patch_settings.text

    u = uuid.uuid4().hex[:12]
    hr_email = f"dd-new-{u}@example.com"
    hr_phone = f"+48123{u[:9]}"
    leadgen = f"dd-new-lg-{u}"
    ad_numeric = 8_100_000_000 + (uuid.uuid4().int % 99_000_000)

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        cand = Candidate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            first_name="Existing",
            last_name="Candidate",
            email=hr_email,
            stage="ready_for_hr",
            status="ready_for_hr",
            company_id=company_id,
        )
        session.add(cand)
        await session.flush()
        session.add(
            WorkforceEmployee(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=str(cand.id),
                display_name="DD New",
                status="onboarding",
            )
        )
        await session.commit()
        old_cand_id = cand.id
        vac_id = vacancy_id

    map_resp = await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vac_id, "note": "test_duplicate_decision_create_new"},
    )
    assert map_resp.status_code == 201, map_resp.text

    payload = _meta_payload(
        vac_id,
        email=hr_email,
        phone=hr_phone,
        lead_id=leadgen,
        ad_id=str(ad_numeric),
        preferred_contact="whatsapp",
        preferred_contact_field="preferred_contact_method",
        country="LK",
        poland_stay_basis="karta_pobytu_(residence_card)",
        poland_stay_basis_field="type_of_residence_in_poland",
        company_name="Meta Logistics",
        company_field="Компания - Название",
    )
    post = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert post.status_code == 200, post.text
    lead_id = post.json()["lead_id"]

    dec = await client.post(
        f"/api/v1/leads/{lead_id}/duplicate-decision",
        headers={**manager_headers, "Content-Type": "application/json"},
        json={"decision": "create_new"},
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["status"] == "needs_routing"

    await satisfy_lead_rodo_via_source_for_tests(client, manager_headers, lead_id)

    proc = await client.post(
        f"/api/v1/leads/{lead_id}/process",
        headers=manager_headers,
    )
    assert proc.status_code == 200, proc.text
    proc_body = proc.json()
    assert proc_body.get("status") == "processed", proc_body
    assert proc_body.get("status") != "duplicate_review"
    new_cand_id = proc_body.get("candidate_id")
    assert new_cand_id
    assert new_cand_id != old_cand_id

    apps = await client.get(
        f"/api/v1/candidates/{new_cand_id}/applications",
        headers=manager_headers,
    )
    assert apps.status_code == 200, apps.text
    app_items = apps.json()
    assert len(app_items) == 1
    assert app_items[0]["lead_id"] == lead_id
    assert app_items[0]["vacancy_id"] == vac_id

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, lead_id)
        assert lead_row is not None
        assert lead_row.status == "processed"
        norm = lead_row.normalized if isinstance(lead_row.normalized, dict) else {}
        override = norm.get("duplicate_override_v1")
        assert isinstance(override, dict)
        ignored = override.get("ignored_candidate_ids")
        assert isinstance(ignored, list) and str(old_cand_id) in [str(x) for x in ignored]
        hist = norm.get("duplicate_decisions_history_v1")
        assert isinstance(hist, list) and any(
            str(x.get("decision")) == "create_new" for x in hist if isinstance(x, dict)
        )

    proc2 = await client.post(
        f"/api/v1/leads/{lead_id}/process",
        headers=manager_headers,
    )
    assert proc2.status_code == 200, proc2.text
    proc2_body = proc2.json()
    assert proc2_body.get("candidate_id") == new_cand_id
    assert proc2_body.get("status") != "duplicate_review"

    async with async_session_maker() as session:
        lead_row2 = await session.get(Lead, lead_id)
        assert lead_row2 is not None
        norm2 = lead_row2.normalized if isinstance(lead_row2.normalized, dict) else {}
        override2 = norm2.get("duplicate_override_v1")
        assert isinstance(override2, dict)
        ignored2 = override2.get("ignored_candidate_ids")
        assert isinstance(ignored2, list) and str(old_cand_id) in [str(x) for x in ignored2]

        app_n = await session.execute(
            select(func.count())
            .select_from(RecruitmentApplication)
            .where(
                RecruitmentApplication.tenant_id == tenant_id,
                RecruitmentApplication.lead_id == lead_id,
            )
        )
        assert int(app_n.scalar_one() or 0) == 1


@pytest.mark.anyio
async def test_duplicate_decision_ignore_skips_suggested_without_candidate(client, manager_headers, tenant_id) -> None:
    """ignore: HR duplicate_review cleared; no candidate until operator runs process (MVP: needs_routing)."""
    patch_settings = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": True, "leads_processing_mode_v1": "automatic"},
    )
    assert patch_settings.status_code == 200, patch_settings.text

    u = uuid.uuid4().hex[:10]
    hr_email = f"dd-ign-{u}@example.com"
    hr_phone = f"+48141{u[:8]}"

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        cand = Candidate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            first_name="Existing",
            last_name="Candidate",
            email=hr_email,
            stage="ready_for_hr",
            status="ready_for_hr",
            company_id=company_id,
        )
        session.add(cand)
        await session.flush()
        session.add(
            WorkforceEmployee(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=str(cand.id),
                display_name="DD Ignore",
                status="onboarding",
            )
        )
        await session.commit()
        old_cand_id = cand.id
        vac_id = vacancy_id

    payload = _meta_payload(vac_id, email=hr_email, phone=hr_phone, lead_id=f"dd-ign-lg-{u}")
    post = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert post.status_code == 200, post.text
    lead_id = post.json()["lead_id"]
    assert post.json()["status"] == "duplicate_review"

    dec = await client.post(
        f"/api/v1/leads/{lead_id}/duplicate-decision",
        headers={**manager_headers, "Content-Type": "application/json"},
        json={"decision": "ignore", "note": "not a duplicate"},
    )
    assert dec.status_code == 200, dec.text
    body = dec.json()
    assert body["status"] == "needs_routing"
    assert body.get("candidate_id") in (None, "")

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, lead_id)
        assert lead_row is not None
        assert lead_row.candidate_id is None
        norm = lead_row.normalized if isinstance(lead_row.normalized, dict) else {}
        assert norm.get("duplicate_match_v1") is None
        res = norm.get("duplicate_resolution_v1")
        assert isinstance(res, dict) and res.get("outcome") == "ignore"
        override = norm.get("duplicate_override_v1")
        assert isinstance(override, dict)
        ignored = override.get("ignored_candidate_ids")
        assert isinstance(ignored, list) and str(old_cand_id) in [str(x) for x in ignored]
        hist = norm.get("duplicate_decisions_history_v1")
        assert isinstance(hist, list)
        last_dec = next((x for x in reversed(hist) if isinstance(x, dict)), None)
        assert last_dec is not None and last_dec.get("decision") == "ignore"

        log_row = await session.execute(
            select(ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == "lead.duplicate_decision",
                ActivityLog.target_id == lead_id,
            )
            .order_by(desc(ActivityLog.created_at))
            .limit(1)
        )
        lp = log_row.scalar_one_or_none()
        assert isinstance(lp, dict) and lp.get("decision") == "ignore"

        app_cnt_before = await session.execute(
            select(func.count())
            .select_from(RecruitmentApplication)
            .where(
                RecruitmentApplication.tenant_id == tenant_id,
                RecruitmentApplication.lead_id == lead_id,
            )
        )
        assert int(app_cnt_before.scalar_one() or 0) == 0

    await satisfy_lead_rodo_via_source_for_tests(client, manager_headers, lead_id)

    proc = await client.post(
        f"/api/v1/leads/{lead_id}/process",
        headers=manager_headers,
    )
    assert proc.status_code == 200, proc.text
    proc_body = proc.json()
    assert proc_body.get("status") == "processed", proc_body
    new_cand_id = proc_body.get("candidate_id")
    assert new_cand_id
    assert new_cand_id != str(old_cand_id)

    apps = await client.get(
        f"/api/v1/candidates/{new_cand_id}/applications",
        headers=manager_headers,
    )
    assert apps.status_code == 200, apps.text
    app_items = apps.json()
    assert len(app_items) == 1
    assert app_items[0]["lead_id"] == lead_id
    assert app_items[0]["vacancy_id"] == vac_id
    assert app_items[0]["status"] == "active"


def test_pick_lead_assignee_fallback_roles_no_legacy_pg_aliases() -> None:
    """Postgres users.role enum has no owner/admin/manager literals — do not bind them in SQL."""
    src = inspect.getsource(_helpers._pick_lead_assignee_id)
    assert '"owner"' not in src and "'owner'" not in src
    assert '"admin"' not in src and "'admin'" not in src
    assert '"manager"' not in src and "'manager'" not in src
    assert "User.role.in_([Role.administrator, Role.supervisor])" in src
