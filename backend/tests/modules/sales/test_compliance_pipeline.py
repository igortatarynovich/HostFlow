"""Sales compliance / ops → Communication Pipeline binder (ADR-031 PR-1)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.modules.sales.communication.compliance_pipeline import (
    PURPOSE_GDPR_NOTICE,
    SalesCompliancePipelineError,
    ensure_sales_compliance_pipeline_binding,
    lead_is_sales_destination,
    purpose_for_ops_event,
    resolve_lead_uses_sales_compliance_pipeline,
)


def test_purpose_for_ops_event_mapping() -> None:
    assert purpose_for_ops_event("application_received") is None
    assert purpose_for_ops_event("lead_rejected") == "intake_rejection_notice"
    assert purpose_for_ops_event("moving_forward") == "moving_forward_notice"
    assert purpose_for_ops_event("unknown") is None


def test_lead_is_sales_destination_from_result_link() -> None:
    lead = SimpleNamespace(
        id="lead-1",
        normalized={
            "intake_result_link_v1": {
                "result_type": "sales_inquiry",
                "sales_inquiry_id": "si-1",
            }
        },
    )
    assert lead_is_sales_destination(lead) is True


def test_lead_is_sales_destination_rejects_application() -> None:
    lead = SimpleNamespace(
        id="lead-1",
        normalized={
            "intake_result_link_v1": {
                "result_type": "application",
                "application_id": "app-1",
            }
        },
    )
    assert lead_is_sales_destination(lead) is False


def test_lead_is_sales_destination_from_routing_stamp() -> None:
    lead = SimpleNamespace(
        id="lead-1",
        normalized={"acquisition_routing_v1": {"route_intent": "sales_inquiry"}},
    )
    assert lead_is_sales_destination(lead) is True


@pytest.mark.asyncio
async def test_resolve_uses_existing_sales_inquiry() -> None:
    lead = SimpleNamespace(id="lead-1", normalized={})
    inquiry = SimpleNamespace(id="si-1", tenant_id="t1", lead_id="lead-1")
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=inquiry)
    assert (
        await resolve_lead_uses_sales_compliance_pipeline(
            db, tenant_id="t1", lead=lead
        )
        is True
    )


@pytest.mark.asyncio
async def test_binder_rejects_recruitment_bound_transport_lead() -> None:
    lead = SimpleNamespace(
        id="lead-1",
        own_company_id="oc-1",
        normalized={
            "intake_result_link_v1": {
                "result_type": "application",
                "application_id": "app-1",
            }
        },
    )
    db = AsyncMock()
    with pytest.raises(SalesCompliancePipelineError) as exc:
        await ensure_sales_compliance_pipeline_binding(
            db,
            tenant_id="t1",
            lead=lead,
            purpose=PURPOSE_GDPR_NOTICE,
        )
    assert exc.value.details.get("reason") == "recruitment_result_bound"
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_binder_refuses_to_invent_si_for_non_sales() -> None:
    lead = SimpleNamespace(id="lead-1", own_company_id="oc-1", normalized={})
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    db.scalar = AsyncMock(return_value=None)
    with pytest.raises(SalesCompliancePipelineError) as exc:
        await ensure_sales_compliance_pipeline_binding(
            db,
            tenant_id="t1",
            lead=lead,
            purpose=PURPOSE_GDPR_NOTICE,
        )
    assert exc.value.details.get("reason") == "not_sales_destination"


@pytest.mark.asyncio
async def test_binder_creates_email_thread_and_result_link() -> None:
    lead = SimpleNamespace(
        id="lead-1",
        own_company_id="oc-1",
        normalized={
            "intake_result_link_v1": {
                "result_type": "sales_inquiry",
                "sales_inquiry_id": "si-1",
            }
        },
    )
    inquiry = SimpleNamespace(id="si-1", tenant_id="t1", lead_id="lead-1")
    db = AsyncMock()
    db.get = AsyncMock(return_value=inquiry)
    # first scalar after get: existing bound thread
    db.scalar = AsyncMock(return_value=None)
    db.flush = AsyncMock()

    fake_link = MagicMock()
    with (
        patch(
            "backend.app.modules.sales.communication.compliance_pipeline"
            ".attach_thread_result_link",
            new_callable=AsyncMock,
            return_value=fake_link,
        ) as attach,
        patch(
            "backend.app.modules.sales.communication.compliance_pipeline"
            ".ensure_thread_entity_link",
            new_callable=AsyncMock,
        ) as ensure_g13,
    ):
        binding = await ensure_sales_compliance_pipeline_binding(
            db,
            tenant_id="t1",
            lead=lead,
            purpose=PURPOSE_GDPR_NOTICE,
            locale="pl",
        )

    assert binding.sales_inquiry_id == "si-1"
    assert binding.communication_purpose == PURPOSE_GDPR_NOTICE
    assert binding.locale == "pl"
    assert binding.template.module_owner == "sales"
    assert binding.template.communication_purpose == PURPOSE_GDPR_NOTICE
    db.add.assert_called()
    attach.assert_awaited()
    assert ensure_g13.await_count >= 2
