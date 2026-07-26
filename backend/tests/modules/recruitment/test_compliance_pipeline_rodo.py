"""Recruitment RODO → Communication Pipeline binder (ADR-031 PR-3)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.modules.recruitment.communication.compliance_pipeline import (
    PURPOSE_GDPR_NOTICE,
    RecruitmentCompliancePipelineError,
    ensure_recruitment_compliance_pipeline_binding,
    resolve_lead_uses_recruitment_compliance_pipeline,
)
from backend.app.modules.recruitment.communication.policy_adapter import (
    RecruitmentCommunicationPolicyAdapter,
)
from backend.app.communications.policy_contract import CommunicationPolicyRequest
from backend.app.communications.intent_policy import evaluate_intent_policy


def test_policy_allows_gdpr_notice_on_application() -> None:
    adapter = RecruitmentCommunicationPolicyAdapter()
    decision = adapter.evaluate(
        CommunicationPolicyRequest(
            module_owner="recruitment",
            communication_domain="recruitment",
            communication_purpose=PURPOSE_GDPR_NOTICE,
            channel="email",
            result_type="application",
            result_id="app-1",
        )
    )
    assert decision.allowed is True


def test_intent_allows_application_gdpr_notice() -> None:
    result = evaluate_intent_policy(
        intent_key="gdpr_notice",
        entity_type="application",
        channel="email",
        automation=True,
    )
    assert result.allowed is True


@pytest.mark.asyncio
async def test_resolve_recruitment_with_vacancy() -> None:
    lead = SimpleNamespace(
        id="l1",
        vacancy_id="v1",
        funnel_id=None,
        normalized={},
    )
    assert (
        await resolve_lead_uses_recruitment_compliance_pipeline(
            AsyncMock(), tenant_id="t1", lead=lead
        )
        is True
    )


@pytest.mark.asyncio
async def test_resolve_rejects_sales_bound() -> None:
    lead = SimpleNamespace(
        id="l1",
        vacancy_id="v1",
        funnel_id=None,
        normalized={
            "intake_result_link_v1": {
                "result_type": "sales_inquiry",
                "sales_inquiry_id": "si-1",
            }
        },
    )
    assert (
        await resolve_lead_uses_recruitment_compliance_pipeline(
            AsyncMock(), tenant_id="t1", lead=lead
        )
        is False
    )


@pytest.mark.asyncio
async def test_binder_creates_thread_for_existing_application() -> None:
    lead = SimpleNamespace(
        id="lead-1",
        own_company_id="oc-1",
        vacancy_id="v1",
        funnel_id=None,
        normalized={
            "intake_result_link_v1": {
                "result_type": "application",
                "application_id": "app-1",
            }
        },
    )
    app = SimpleNamespace(id="app-1", tenant_id="t1", candidate_id="cand-1", lead_id="lead-1")
    db = AsyncMock()
    db.get = AsyncMock(return_value=app)
    db.scalar = AsyncMock(return_value=None)
    db.flush = AsyncMock()

    with (
        patch(
            "backend.app.modules.recruitment.communication.compliance_pipeline"
            ".attach_thread_result_link",
            new_callable=AsyncMock,
        ) as attach,
        patch(
            "backend.app.modules.recruitment.communication.compliance_pipeline"
            ".ensure_thread_entity_link",
            new_callable=AsyncMock,
        ) as g13,
    ):
        binding = await ensure_recruitment_compliance_pipeline_binding(
            db,
            tenant_id="t1",
            lead=lead,
            purpose=PURPOSE_GDPR_NOTICE,
            locale="pl",
        )

    assert binding.application_id == "app-1"
    assert binding.candidate_id == "cand-1"
    assert binding.communication_purpose == PURPOSE_GDPR_NOTICE
    assert binding.template.module_owner == "recruitment"
    db.add.assert_called()
    attach.assert_awaited()
    assert g13.await_count >= 3


@pytest.mark.asyncio
async def test_binder_rejects_sales_bound() -> None:
    lead = SimpleNamespace(
        id="lead-1",
        vacancy_id="v1",
        normalized={
            "intake_result_link_v1": {
                "result_type": "sales_inquiry",
                "sales_inquiry_id": "si-1",
            }
        },
    )
    with pytest.raises(RecruitmentCompliancePipelineError) as exc:
        await ensure_recruitment_compliance_pipeline_binding(
            AsyncMock(), tenant_id="t1", lead=lead
        )
    assert exc.value.details.get("reason") == "sales_bound"


@pytest.mark.asyncio
async def test_recruitment_rodo_uses_prepare_and_send_not_smtp() -> None:
    from backend.app.services.lead_rodo import _send_lead_rodo_via_recruitment_pipeline
    from backend.app.modules.recruitment.communication.compliance_pipeline import (
        RecruitmentCompliancePipelineBinding,
    )
    from backend.app.communications.template_metadata import build_template_metadata
    from backend.app.modules.recruitment.communication.policy_adapter import POLICY_VERSION

    lead = SimpleNamespace(
        id="lead-1",
        own_company_id="oc-1",
        normalized={"email": "a@b.test", "first_name": "Ada"},
    )
    db = AsyncMock()
    db.flush = AsyncMock()
    template = build_template_metadata(
        template_id="tpl_test",
        template_version="1",
        module_owner="recruitment",
        communication_domain="recruitment",
        communication_purpose=PURPOSE_GDPR_NOTICE,
        supported_channels=["email"],
        supported_locales=["pl"],
        lifecycle_status="active",
        policy_version=POLICY_VERSION,
    )
    binding = RecruitmentCompliancePipelineBinding(
        thread_id="th-1",
        application_id="app-1",
        candidate_id="cand-1",
        communication_purpose=PURPOSE_GDPR_NOTICE,
        template=template,
        locale="pl",
    )
    auth = MagicMock()
    auth.allowed = True
    auth.reason_code = None
    auth.to_dict = MagicMock(return_value={"allowed": True})

    with (
        patch(
            "backend.app.modules.recruitment.communication.compliance_pipeline"
            ".ensure_recruitment_compliance_pipeline_binding",
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            "backend.app.communications.send_pipeline.authorize_outbound_communication",
            new_callable=AsyncMock,
            return_value=auth,
        ),
        patch(
            "backend.app.communications.prepare_send.prepare_and_send_communication",
            new_callable=AsyncMock,
        ) as prep,
        patch(
            "backend.app.services.lead_rodo.log_audit_event",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.app.services.lead_rodo.send_email_for_tenant",
            new_callable=AsyncMock,
        ) as smtp,
    ):
        ok, msg = await _send_lead_rodo_via_recruitment_pipeline(
            db,
            tenant_id="t1",
            lead=lead,
            actor_id=None,
            email="a@b.test",
            channel="email",
            subject="RODO",
            body="body",
            rodo_link="https://example.test/rodo",
            rodo_version_id="v1",
            auto_trigger=None,
            ingest_source="meta",
            first_name="Ada",
        )

    assert ok is True
    assert "sent" in msg.lower()
    prep.assert_awaited_once()
    smtp.assert_not_called()
    assert lead.normalized["rodo"]["delivery"] == "communication_pipeline"
    assert lead.normalized["rodo"]["application_id"] == "app-1"
