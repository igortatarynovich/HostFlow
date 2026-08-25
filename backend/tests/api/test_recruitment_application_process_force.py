"""Отклики → create candidate must succeed after vacancy bind even without Meta flight matrix."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.models import Lead
from backend.tests.api.lead_rodo_test_utils import satisfy_lead_rodo_via_source_for_tests
from backend.tests.api.test_leads_meta import _ensure_company, _ensure_vacancy


@pytest.mark.anyio
async def test_recruitment_process_creates_candidate_without_intake_flight_context(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    """Regression: binding a vacancy then Create candidate must not die on no_intake_context."""
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        lead_id = str(uuid.uuid4())
        email = f"otklik-force-{uuid.uuid4().hex[:10]}@example.com"
        phone = f"+48111{uuid.uuid4().hex[:9]}"
        payload = {
            "id": f"lg-force-{uuid.uuid4().hex[:12]}",
            "created_time": "2026-07-21T10:00:00+0000",
            "ad_id": "999000111",
            "form_id": "",
            "field_data": [
                {"name": "full_name", "values": ["Force Otklik"]},
                {"name": "email", "values": [email]},
                {"name": "phone_number", "values": [phone]},
            ],
        }
        normalized = {
            "email": email,
            "phone": phone,
            "full_name": "Force Otklik",
            "first_name": "Force",
            "last_name": "Otklik",
            "vacancy_id": vacancy_id,
            # Acquisition matrix has nothing to resolve → would be no_intake_context without force.
            "acquisition_routing_v1": {
                "status": "unresolved",
                "unresolved_reason": "no_intake_context",
            },
        }
        await session.execute(
            sa.text(
                """
                INSERT INTO leads (
                  id, tenant_id, company_id, vacancy_id, source, lead_type, lead_target_type,
                  payload, normalized, status, error, external_id, created_at
                )
                VALUES (
                  :id, :tenant_id, :company_id, :vacancy_id, 'meta', 'candidate', 'candidate',
                  CAST(:payload AS jsonb), CAST(:normalized AS jsonb),
                  'needs_routing', 'no_intake_context', :ext, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": lead_id,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "vacancy_id": vacancy_id,
                "payload": __import__("json").dumps(payload),
                "normalized": __import__("json").dumps(normalized),
                "ext": payload["id"],
            },
        )
        await session.commit()

    conf = await client.post(
        f"/api/v1/recruitment/applications/{lead_id}/confirm-vacancy",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id},
    )
    assert conf.status_code == 200, conf.text

    await satisfy_lead_rodo_via_source_for_tests(client, manager_headers, lead_id)

    proc = await client.post(
        f"/api/v1/recruitment/applications/{lead_id}/process",
        headers=manager_headers,
    )
    assert proc.status_code == 200, proc.text
    body = proc.json()
    assert body.get("candidate_id"), body
    assert body.get("message") in (None, "")
    assert (body.get("application") or {}).get("outcome_entity_type") == "candidate"

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, lead_id)
        assert lead_row is not None
        assert lead_row.candidate_id == body["candidate_id"]
        assert lead_row.status == "processed"


@pytest.mark.anyio
async def test_recruitment_process_auto_binds_vacancy_from_meta_ads_map(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    """Create candidate without manual vacancy UI when Meta ad→vacancy map exists."""
    import json

    from backend.app.models import MetaAdsMap

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        ad_id = 9_100_000_000 + (uuid.uuid4().int % 90_000_000)
        session.add(
            MetaAdsMap(
                tenant_id=tenant_id,
                ad_id=ad_id,
                vacancy_id=vacancy_id,
                note="test_auto_bind_from_ad_map",
            )
        )
        lead_id = str(uuid.uuid4())
        email = f"otklik-admap-{uuid.uuid4().hex[:10]}@example.com"
        phone = f"+48222{uuid.uuid4().hex[:9]}"
        payload = {
            "id": f"lg-admap-{uuid.uuid4().hex[:12]}",
            "created_time": "2026-07-21T10:00:00+0000",
            "ad_id": str(ad_id),
            "form_id": "",
            "field_data": [
                {"name": "full_name", "values": ["Admap Otklik"]},
                {"name": "email", "values": [email]},
                {"name": "phone_number", "values": [phone]},
            ],
        }
        normalized = {
            "email": email,
            "phone": phone,
            "full_name": "Admap Otklik",
            "first_name": "Admap",
            "last_name": "Otklik",
            "ad_id": ad_id,
            "acquisition_routing_v1": {
                "status": "unresolved",
                "unresolved_reason": "no_intake_context",
            },
        }
        await session.execute(
            sa.text(
                """
                INSERT INTO leads (
                  id, tenant_id, company_id, vacancy_id, ad_id, source, lead_type, lead_target_type,
                  payload, normalized, status, error, external_id, created_at
                )
                VALUES (
                  :id, :tenant_id, :company_id, NULL, :ad_id, 'meta', 'candidate', 'candidate',
                  CAST(:payload AS jsonb), CAST(:normalized AS jsonb),
                  'needs_routing', 'no_intake_context', :ext, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": lead_id,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "ad_id": ad_id,
                "payload": json.dumps(payload),
                "normalized": json.dumps(normalized),
                "ext": payload["id"],
            },
        )
        await session.commit()

    await satisfy_lead_rodo_via_source_for_tests(client, manager_headers, lead_id)

    # No confirm-vacancy call — prepare must pull vacancy from meta_ads_map.
    proc = await client.post(
        f"/api/v1/recruitment/applications/{lead_id}/process",
        headers=manager_headers,
    )
    assert proc.status_code == 200, proc.text
    body = proc.json()
    assert body.get("candidate_id"), body
    assert (body.get("application") or {}).get("extensions", {}).get("vacancy_id") == vacancy_id

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, lead_id)
        assert lead_row is not None
        assert str(lead_row.vacancy_id) == vacancy_id
        assert lead_row.candidate_id == body["candidate_id"]
