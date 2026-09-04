"""Recruitment-bound RODO: delivery_failed → ops retry → delivered lifts the gate.

Sales-bound proof lives in ``test_lead_rodo_bound_retry.py``. This is the other
ADR-031 destination: vacancy intent → Application binder → Communication Pipeline.
SMTP is the session mock from conftest (``EMAIL_DELIVERY_MODE=mock``).
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from backend.app.db.session import async_session_maker
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.services.lead_rodo import mark_lead_rodo_failed
from backend.app.services.lead_rodo_obligation import current_compliance_state


async def _own_company_id(session, tenant_id: str) -> str:
    row = await session.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    own_company_id = row.scalar_one_or_none()
    if own_company_id is None:
        own_company_id = str(uuid.uuid4())
        session.add(
            OwnCompany(
                id=own_company_id,
                tenant_id=tenant_id,
                name=f"OC {uuid.uuid4().hex[:6]}",
            )
        )
        await session.flush()
    return str(own_company_id)


async def _ensure_company(session, tenant_id: str) -> str:
    result = await session.execute(
        sa.text("SELECT id FROM companies WHERE tenant_id = :tenant LIMIT 1"),
        {"tenant": tenant_id},
    )
    company_id = result.scalar_one_or_none()
    if company_id:
        return str(company_id)
    company_id = str(uuid.uuid4())
    await session.execute(
        sa.text(
            """
            INSERT INTO companies (id, tenant_id, name, party_entity_type)
            VALUES (:id, :tenant_id, :name, :party_entity_type)
            """
        ),
        {
            "id": company_id,
            "tenant_id": tenant_id,
            "name": f"RODO Rec {uuid.uuid4().hex[:6]}",
            "party_entity_type": "company",
        },
    )
    await session.flush()
    return company_id


async def _ensure_vacancy(session, tenant_id: str, company_id: str) -> str:
    vacancy_id = str(uuid.uuid4())
    await session.execute(
        sa.text(
            """
            INSERT INTO vacancies (id, tenant_id, company_id, title, status, is_active, is_archived)
            VALUES (:id, :tenant_id, :company_id, :title, :status, :is_active, :is_archived)
            """
        ),
        {
            "id": vacancy_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "title": "RODO bound retry",
            "status": "open",
            "is_active": True,
            "is_archived": False,
        },
    )
    await session.flush()
    return vacancy_id


async def _rodo_block(lead_id: str) -> dict:
    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        raw = norm.get("rodo")
        return dict(raw) if isinstance(raw, dict) else {}


@pytest.mark.anyio
async def test_recruitment_bound_delivery_failed_retry_delivers_and_lifts_gate(
    client, manager_headers, tenant_id
):
    suffix = uuid.uuid4().hex[:10]
    email = f"rodo-rec-{suffix}@example.test"

    async with async_session_maker() as session:
        own_company_id = await _own_company_id(session, tenant_id)
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        lead = Lead(
            id=str(uuid.uuid4()),
            tenant_id=str(tenant_id),
            own_company_id=own_company_id,
            company_id=company_id,
            vacancy_id=vacancy_id,
            source="manual",
            lead_type="candidate",
            lead_target_type="candidate",
            payload={"email": email},
            normalized={
                "email": email,
                "first_name": "Bound",
                "last_name": "Recruit",
                "acquisition_routing_v1": {"route_intent": "candidate_application"},
            },
            external_id=f"rec-rodo-{suffix}",
        )
        session.add(lead)
        await session.flush()
        mark_lead_rodo_failed(lead, reason="previous_smtp_failure")
        flag_modified(lead, "normalized")
        await session.commit()
        lead_id = str(lead.id)

    before = await _rodo_block(lead_id)
    assert current_compliance_state(before) == "delivery_failed"

    queued = await client.get(
        "/api/v1/leads/compliance/rodo/queue",
        headers=manager_headers,
        params={"limit": 200, "state": "delivery_failed"},
    )
    assert queued.status_code == 200, queued.text
    queued_ids = {item.get("lead_id") for item in (queued.json().get("items") or [])}
    assert lead_id in queued_ids

    retry = await client.post(
        f"/api/v1/leads/{lead_id}/compliance/rodo/retry",
        headers=manager_headers,
    )
    assert retry.status_code == 200, retry.text
    assert retry.json().get("ok") is True

    after = await _rodo_block(lead_id)
    assert current_compliance_state(after) == "delivered"
    assert after.get("status") == "sent"
    assert after.get("delivery") == "communication_pipeline"
    assert after.get("auto_trigger") == "ops_retry"
    assert after.get("application_id")
    evidence = after.get("delivery_evidence") if isinstance(after.get("delivery_evidence"), dict) else {}
    assert evidence.get("state") == "delivered"
    assert evidence.get("path") == "communication_pipeline"

    queue = await client.get(
        "/api/v1/leads/compliance/rodo/queue",
        headers=manager_headers,
        params={"limit": 200},
    )
    assert queue.status_code == 200, queue.text
    ids = {item.get("lead_id") for item in (queue.json().get("items") or [])}
    assert lead_id not in ids

    lifted = await client.patch(
        f"/api/v1/leads/{lead_id}",
        headers=manager_headers,
        json={"stage": "contacted"},
    )
    assert lifted.status_code == 200, lifted.text
    assert lifted.json().get("stage") == "contacted"
