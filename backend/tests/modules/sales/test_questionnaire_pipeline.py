"""Sales questionnaire → Communication Pipeline binder."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.modules.sales.communication.questionnaire_pipeline import (
    PURPOSE_QUALIFICATION_QUESTIONNAIRE,
    SalesQuestionnairePipelineError,
    ensure_sales_questionnaire_pipeline_binding,
    sales_questionnaire_template_metadata,
)


def test_sales_questionnaire_template_metadata_matches_policy() -> None:
    meta = sales_questionnaire_template_metadata()
    assert meta.module_owner == "sales"
    assert meta.communication_domain == "sales"
    assert meta.communication_purpose == PURPOSE_QUALIFICATION_QUESTIONNAIRE
    assert "email" in meta.supported_channels
    assert meta.lifecycle_status == "active"


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
    with pytest.raises(SalesQuestionnairePipelineError) as exc:
        await ensure_sales_questionnaire_pipeline_binding(
            db, tenant_id="t1", lead=lead, locale="pl"
        )
    assert exc.value.details.get("reason") == "recruitment_result_bound"
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_binder_creates_email_thread_and_result_link() -> None:
    lead = SimpleNamespace(
        id="lead-1",
        own_company_id="oc-1",
        normalized={"email": "a@b.test"},
    )
    inquiry = SimpleNamespace(id="si-1", tenant_id="t1", lead_id="lead-1")
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    # first scalar: SalesInquiry by lead_id; second: existing bound thread
    db.scalar = AsyncMock(side_effect=[inquiry, None])
    db.flush = AsyncMock()

    fake_link = MagicMock()
    with (
        patch(
            "backend.app.modules.sales.communication.questionnaire_pipeline"
            ".ensure_sales_inquiry_for_transport_lead",
            new_callable=AsyncMock,
        ) as ensure_si,
        patch(
            "backend.app.modules.sales.communication.questionnaire_pipeline"
            ".attach_thread_result_link",
            new_callable=AsyncMock,
            return_value=fake_link,
        ) as attach,
        patch(
            "backend.app.modules.sales.communication.questionnaire_pipeline"
            ".ensure_thread_entity_link",
            new_callable=AsyncMock,
        ) as ensure_g13,
    ):
        binding = await ensure_sales_questionnaire_pipeline_binding(
            db, tenant_id="t1", lead=lead, locale="pl", actor_user_id="u1"
        )
    ensure_si.assert_not_awaited()

    assert binding.sales_inquiry_id == "si-1"
    assert binding.communication_purpose == PURPOSE_QUALIFICATION_QUESTIONNAIRE
    assert binding.template.template_id.startswith("tpl_sales_")
    assert binding.locale == "pl"
    assert binding.thread_id
    db.add.assert_called_once()
    attach.assert_awaited_once()
    assert attach.await_args.kwargs["opaque"].module_owner == "sales"
    assert attach.await_args.kwargs["opaque"].result_type == "sales_inquiry"
    assert attach.await_args.kwargs["opaque"].result_id == "si-1"
    assert ensure_g13.await_count == 2
    g13_types = {c.kwargs["entity_type"] for c in ensure_g13.await_args_list}
    assert g13_types == {"sales_inquiry", "lead"}
