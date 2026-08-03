"""Stage 3 slice 3 — SalesInquiry product identity on Sales HTTP."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from backend.app.modules.applications.mappers import (
    lead_to_sales_inquiry,
    sales_inquiry_to_application,
)


def test_sales_inquiry_to_application_uses_si_product_id():
    lead_id = str(uuid4())
    si_id = str(uuid4())
    lead = SimpleNamespace(
        id=lead_id,
        normalized={
            "company_name_hint": "Acme Sp. z o.o.",
            "field_answers": [{"name": "custom", "values": ["1"]}],
            "additional_answers": [{"name": "custom", "values": ["1"]}],
        },
        company_name=None,
        source="meta",
        stage="new",
        status="new",
        assigned_to=None,
        recruiter_id=None,
        next_action_type=None,
        updated_at=None,
        created_at=None,
        priority=None,
        converted_client_id=None,
        client_account_id=None,
        payload={"entry": []},
        phone=None,
        email=None,
        full_name=None,
    )
    inquiry = SimpleNamespace(id=si_id)
    app = sales_inquiry_to_application(inquiry, lead)
    assert app.id == si_id
    assert app.sales_inquiry_id == si_id
    assert app.transport_lead_id == lead_id
    assert app.extensions["transport_lead_id"] == lead_id
    assert app.title == "Acme Sp. z o.o."
    assert any(row["name"] == "custom" for row in app.extensions["meta_form_answers"])
    # Sales list never projects recruitment module.
    assert app.module == "sales"

    legacy = lead_to_sales_inquiry(lead)
    assert legacy.id == lead_id
    assert legacy.transport_lead_id == lead_id
