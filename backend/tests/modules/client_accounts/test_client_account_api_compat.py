"""Stage 1A PR-3: API response compatibility for ClientAccount."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.app.models import Lead
from backend.app.modules.applications.mappers import lead_to_sales_inquiry
from backend.app.modules.leads.schemas import LeadOut


def _sales_lead(**overrides) -> Lead:
    lead_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    base = {
        "id": lead_id,
        "tenant_id": str(uuid.uuid4()),
        "own_company_id": str(uuid.uuid4()),
        "source": "meta",
        "lead_type": "client",
        "lead_target_type": "client_lead",
        "status": "processed",
        "stage": "converted",
        "normalized": {
            "company_name": "Acme Transport",
            "full_name": "Jane Doe",
            "email": "jane@example.com",
        },
        "created_at": now,
    }
    base.update(overrides)
    return Lead(**base)


@pytest.mark.anyio
async def test_lead_out_exposes_client_account_id_field() -> None:
    account_id = uuid.uuid4()
    company_id = uuid.uuid4()
    payload = LeadOut(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        own_company_id=uuid.uuid4(),
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
        status="processed",
        stage="converted",
        payload={},
        converted_client_id=company_id,
        client_account_id=account_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert payload.client_account_id == account_id
    assert payload.converted_client_id == company_id


def test_sales_inquiry_prefers_client_account_outcome() -> None:
    account_id = str(uuid.uuid4())
    company_id = str(uuid.uuid4())
    lead = _sales_lead(
        client_account_id=account_id,
        converted_client_id=company_id,
    )
    app = lead_to_sales_inquiry(lead)

    assert app.extensions["client_account_id"] == account_id
    assert app.extensions["company_id"] == company_id
    assert app.outcome_entity_id == account_id
    assert app.outcome_entity_type == "client_account"
    assert app.status == "completed"


def test_sales_inquiry_legacy_company_only_outcome() -> None:
    company_id = str(uuid.uuid4())
    lead = _sales_lead(converted_client_id=company_id, client_account_id=None)
    app = lead_to_sales_inquiry(lead)

    assert app.extensions.get("client_account_id") is None
    assert app.extensions["company_id"] == company_id
    assert app.outcome_entity_id == company_id
    assert app.outcome_entity_type == "client"
    assert app.status == "completed"


def test_sales_inquiry_unconverted_has_no_outcome() -> None:
    lead = _sales_lead(status="new", stage="new", converted_client_id=None, client_account_id=None)
    app = lead_to_sales_inquiry(lead)

    assert app.outcome_entity_id is None
    assert app.outcome_entity_type is None
    assert app.status == "new"
