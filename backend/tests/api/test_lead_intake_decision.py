"""Intake Resolution MVP slice 2: POST /leads/{id}/intake-decision + process gating."""

from __future__ import annotations

import json
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import desc, select

from backend.app.core.settings import settings
from backend.app.db.session import async_session_maker
from backend.app.models import Lead, LeadImportJob, RecruitmentApplication
from backend.app.models.audit import ActivityLog
from backend.app.models.lead_import_job import LeadImportJobStatus
from backend.app.modules.leads import service as leads_service
from backend.app.services.imports.leads import IMPORT_SOURCE, _normalize_row, run_import_job
from backend.tests.api.test_leads_meta import (
    _ensure_company,
    _ensure_meta_settings,
    _ensure_vacancy,
    _meta_payload,
    _signature_for_payload,
)
from backend.tests.api.lead_rodo_test_utils import satisfy_lead_rodo_via_source_for_tests


@pytest.mark.anyio
async def test_intake_reject_persists_reason_audit_blocks_process_no_candidate(
    client, manager_headers, tenant_id
):
    patch_settings = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": True, "leads_processing_mode_v1": "assisted"},
    )
    assert patch_settings.status_code == 200, patch_settings.text

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    leadgen = f"lg-intake-rej-{u}"
    ad_numeric = 9_100_000_000 + (uuid.uuid4().int % 99_000_000)
    map_resp = await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "test_intake_reject"},
    )
    assert map_resp.status_code == 201, map_resp.text

    payload = _meta_payload(
        vacancy_id,
        email=f"intake-rej-{u}@example.com",
        phone=f"+48134{u[:9]}",
        lead_id=leadgen,
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    dec = await client.post(
        f"/api/v1/leads/{lead_id}/intake-decision",
        headers=manager_headers,
        json={"decision": "reject", "reason_code": "salary_mismatch", "note": "below band"},
    )
    assert dec.status_code == 200, dec.text
    body = dec.json()
    ir = (body.get("normalized") or {}).get("intake_resolution_v1") or {}
    assert ir.get("status") == "rejected"
    assert ir.get("reason_code") == "salary_mismatch"
    assert ir.get("note") == "below band"

    proc = await client.post(f"/api/v1/leads/{lead_id}/process", headers=manager_headers)
    assert proc.status_code == 422, proc.text
    assert proc.json().get("detail", {}).get("code") == "INTAKE_REJECTED"

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, lead_id)
        assert lead_row is not None
        assert lead_row.candidate_id is None

    async with async_session_maker() as session:
        row = await session.execute(
            select(ActivityLog)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.target_type == "lead",
                ActivityLog.target_id == str(lead_id),
                ActivityLog.action == "lead.intake_decision.reject",
            )
            .order_by(desc(ActivityLog.created_at))
            .limit(1)
        )
        log = row.scalar_one_or_none()
        assert log is not None


@pytest.mark.anyio
async def test_intake_reject_requires_reason_code(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    leadgen = f"lg-rej-reason-{u}"
    ad_numeric = 9_200_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "x"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"rej-reason-{u}@example.com",
        phone=f"+48135{u[:9]}",
        lead_id=leadgen,
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    bad = await client.post(
        f"/api/v1/leads/{lead_id}/intake-decision",
        headers=manager_headers,
        json={"decision": "reject"},
    )
    assert bad.status_code == 422
    assert "INTAKE_REJECT_REASON_REQUIRED" in bad.text


@pytest.mark.anyio
async def test_intake_request_info_blocks_process(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_300_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "x"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"reqinfo-{u}@example.com",
        phone=f"+48136{u[:9]}",
        lead_id=f"lg-req-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    lead_id = ingest.json()["lead_id"]

    await satisfy_lead_rodo_via_source_for_tests(client, manager_headers, lead_id)

    await client.post(
        f"/api/v1/leads/{lead_id}/intake-decision",
        headers=manager_headers,
        json={"decision": "request_info", "note": "need docs"},
    )
    conf = await client.post(
        f"/api/v1/leads/{lead_id}/confirm-vacancy",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id},
    )
    assert conf.status_code == 200, conf.text

    proc = await client.post(f"/api/v1/leads/{lead_id}/process", headers=manager_headers)
    assert proc.status_code == 422
    assert proc.json().get("detail", {}).get("code") == "INTAKE_INFO_REQUESTED"


@pytest.mark.anyio
async def test_intake_duplicate_review_blocks_process(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_400_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "x"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"duprev-{u}@example.com",
        phone=f"+48137{u[:9]}",
        lead_id=f"lg-dup-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    lead_id = ingest.json()["lead_id"]

    await client.post(
        f"/api/v1/leads/{lead_id}/intake-decision",
        headers=manager_headers,
        json={"decision": "duplicate_review"},
    )
    proc = await client.post(f"/api/v1/leads/{lead_id}/process", headers=manager_headers)
    assert proc.status_code == 422
    assert proc.json().get("detail", {}).get("code") == "DUPLICATE_REVIEW_PENDING"


@pytest.mark.anyio
async def test_pool_intent_process_without_vacancy_creates_candidate_and_application(
    client, manager_headers, tenant_id
):
    patch_settings = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": True, "leads_processing_mode_v1": "assisted"},
    )
    assert patch_settings.status_code == 200, patch_settings.text

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_500_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "pool_path"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"pool-{u}@example.com",
        phone=f"+48138{u[:9]}",
        lead_id=f"lg-pool-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    async with async_session_maker() as session:
        await session.execute(sa.text("UPDATE leads SET vacancy_id = NULL WHERE id = :id"), {"id": lead_id})
        await session.commit()

    pool = await client.post(
        f"/api/v1/leads/{lead_id}/intake-decision",
        headers=manager_headers,
        json={"decision": "pool"},
    )
    assert pool.status_code == 200, pool.text

    await satisfy_lead_rodo_via_source_for_tests(client, manager_headers, lead_id)

    proc = await client.post(f"/api/v1/leads/{lead_id}/process", headers=manager_headers)
    assert proc.status_code == 200, proc.text
    out = proc.json()
    assert out.get("candidate_id")
    assert out["status"] == "processed"

    async with async_session_maker() as session:
        app_cnt = await session.execute(
            select(sa.func.count())
            .select_from(RecruitmentApplication)
            .where(RecruitmentApplication.tenant_id == tenant_id, RecruitmentApplication.lead_id == lead_id)
        )
        assert int(app_cnt.scalar_one() or 0) >= 1


@pytest.mark.anyio
async def test_qualify_after_confirm_vacancy_allows_process(client, manager_headers, tenant_id):
    patch_settings = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": True, "leads_processing_mode_v1": "assisted"},
    )
    assert patch_settings.status_code == 200, patch_settings.text

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_600_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "qual"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"qual-{u}@example.com",
        phone=f"+48139{u[:9]}",
        lead_id=f"lg-qual-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    lead_id = ingest.json()["lead_id"]

    await client.post(
        f"/api/v1/leads/{lead_id}/confirm-vacancy",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id},
    )
    q = await client.post(
        f"/api/v1/leads/{lead_id}/intake-decision",
        headers=manager_headers,
        json={"decision": "qualify"},
    )
    assert q.status_code == 200, q.text

    await satisfy_lead_rodo_via_source_for_tests(client, manager_headers, lead_id)

    proc = await client.post(f"/api/v1/leads/{lead_id}/process", headers=manager_headers)
    assert proc.status_code == 200, proc.text
    assert proc.json().get("candidate_id")


@pytest.mark.anyio
async def test_intake_qualify_coexists_with_legacy_lost_reason_normalized(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_700_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "leg"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"legacy-{u}@example.com",
        phone=f"+48140{u[:9]}",
        lead_id=f"lg-leg-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, lead_id)
        assert lead_row is not None
        n = dict(lead_row.normalized or {})
        n["lead_lost_reason_v1"] = {"at": "2020-01-01T00:00:00+00:00", "code": "legacy_noise"}
        lead_row.normalized = n
        await session.commit()

    q = await client.post(
        f"/api/v1/leads/{lead_id}/intake-decision",
        headers=manager_headers,
        json={"decision": "qualify"},
    )
    assert q.status_code == 200, q.text
    n = q.json().get("normalized") or {}
    assert isinstance(n.get("intake_resolution_v1"), dict)
    assert n["intake_resolution_v1"].get("status") == "qualified"
    lr = n.get("lead_lost_reason_v1")
    assert isinstance(lr, dict)
    assert lr.get("code") == "legacy_noise"


@pytest.mark.anyio
async def test_bulk_single_lead_worker_respects_intake_reject_block_code(client, manager_headers, tenant_id):
    """Bulk / NBA queue must not bypass ``manual_process_block_code`` (same as POST .../process)."""
    patch_settings = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": True, "leads_processing_mode_v1": "assisted"},
    )
    assert patch_settings.status_code == 200, patch_settings.text

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    leadgen = f"lg-bulk-rej-{u}"
    ad_numeric = 9_800_000_000 + (uuid.uuid4().int % 99_000_000)
    map_resp = await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "test_bulk_intake_gate"},
    )
    assert map_resp.status_code == 201, map_resp.text

    payload = _meta_payload(
        vacancy_id,
        email=f"bulk-rej-{u}@example.com",
        phone=f"+48141{u[:9]}",
        lead_id=leadgen,
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    dec = await client.post(
        f"/api/v1/leads/{lead_id}/intake-decision",
        headers=manager_headers,
        json={"decision": "reject", "reason_code": "not_interested"},
    )
    assert dec.status_code == 200, dec.text

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, lead_id)
        assert lead_row is not None
        row = await leads_service._bulk_auto_process_single_lead(
            session,
            tenant_id=str(tenant_id),
            own_company_id=None,
            lead=lead_row,
        )
        assert row["ok"] is False
        assert row["error"] == "INTAKE_REJECTED"
        assert row["lead_id"] == str(lead_id)

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, lead_id)
        assert lead_row is not None
        assert lead_row.candidate_id is None


@pytest.mark.anyio
async def test_csv_reimport_respects_intake_reject_no_conversion(tenant_id, bootstrap):
    """CSV import re-run for needs_routing row must not bypass ``manual_process_block_code``."""
    tid = str(tenant_id)
    admin_id = str(bootstrap["admin_id"])
    u = uuid.uuid4().hex[:10]
    email = f"csv-intake-gate-{u}@example.com"
    phone = f"+486001{u[:7]}"
    row_dict = {"email": email, "phone": phone}
    headers = ["email", "phone"]
    norm_base, _payload_seed, external_id = _normalize_row(tid, row_dict, headers)
    assert external_id.startswith(f"{IMPORT_SOURCE}:")

    lead_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    norm = {
        **norm_base,
        "intake_resolution_v1": {
            "status": "rejected",
            "reason_code": "not_interested",
            "last_decision": "reject",
        },
    }
    async with async_session_maker() as session:
        session.add(
            Lead(
                id=lead_id,
                tenant_id=tid,
                source="csv_import",
                status="needs_routing",
                stage="lost",
                company_id=str(bootstrap["company_id"]),
                payload=dict(row_dict),
                normalized=norm,
                external_id=external_id,
                error="INTAKE_REJECTED",
            )
        )
        session.add(
            LeadImportJob(
                id=job_id,
                tenant_id=tid,
                created_by=admin_id,
                filename="intake_gate.csv",
                status=LeadImportJobStatus.pending,
            )
        )
        await session.commit()

    # Same raw row shape as _normalize_row (import job uses identical parsing).
    csv_bytes = f"email,phone\n{row_dict['email']},{row_dict['phone']}\n".encode("utf-8")
    await run_import_job(
        job_id,
        tenant_id=tid,
        created_by=admin_id,
        filename="intake_gate.csv",
        content=csv_bytes,
    )

    async with async_session_maker() as session:
        job = await session.get(LeadImportJob, job_id)
        assert job is not None
        assert int(job.failed_rows or 0) >= 1
        report = job.error_report or []
        assert any((e.get("error") == "INTAKE_REJECTED") for e in report if isinstance(e, dict))

        lead_row = await session.get(Lead, lead_id)
        assert lead_row is not None
        assert lead_row.candidate_id is None
