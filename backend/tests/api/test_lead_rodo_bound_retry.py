"""Sales-bound RODO: delivery_failed → ops retry → delivered lifts the gate.

The previous ops E2E used unbound leads and correctly fail-closed on
``communication_pipeline_required``. This proof uses a SalesInquiry bind
(ADR-031) so retry can complete through the Communication Pipeline.
SMTP is the session mock from conftest (``EMAIL_DELIVERY_MODE=mock``).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from backend.app.db.session import async_session_maker
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.modules.leads import crud
from backend.app.modules.sales.services.sales_inquiry_service import (
    ensure_sales_inquiry_for_transport_lead,
)
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


async def _rodo_block(lead_id: str) -> dict:
    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        raw = norm.get("rodo")
        return dict(raw) if isinstance(raw, dict) else {}


@pytest.mark.anyio
async def test_sales_bound_delivery_failed_retry_delivers_and_lifts_gate(
    client, manager_headers, tenant_id
):
    suffix = uuid.uuid4().hex[:10]
    email = f"rodo-bound-{suffix}@example.test"

    async with async_session_maker() as session:
        own_company_id = await _own_company_id(session, tenant_id)
        lead = await crud.create_lead(
            session,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            company_id=None,
            vacancy_id=None,
            payload={"email": email},
            normalized={
                "email": email,
                "first_name": "Bound",
                "last_name": "Retry",
                "acquisition_routing_v1": {"route_intent": "sales_inquiry"},
            },
            ad_id=None,
            source="manual",
            external_id=f"si-rodo-{suffix}",
            lead_type="client",
            lead_target_type="client_lead",
        )
        inquiry = await ensure_sales_inquiry_for_transport_lead(
            session,
            tenant_id=str(tenant_id),
            lead=lead,
            source="manual",
        )
        mark_lead_rodo_failed(lead, reason="previous_smtp_failure")
        flag_modified(lead, "normalized")
        await session.commit()
        lead_id = str(lead.id)
        inquiry_id = str(inquiry.id)

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
    assert after.get("sales_inquiry_id") == inquiry_id
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
