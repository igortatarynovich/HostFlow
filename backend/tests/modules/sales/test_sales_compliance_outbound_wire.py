"""Sales-bound lead RODO / ops via Communication Pipeline (ADR-031 PR-1)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.modules.sales.communication.compliance_pipeline import (
    PURPOSE_GDPR_NOTICE,
    PURPOSE_SUBMISSION_ACK,
    SalesCompliancePipelineBinding,
)
from backend.app.communications.template_metadata import build_template_metadata
from backend.app.modules.sales.communication.policy_adapter import POLICY_VERSION


def _binding(*, purpose: str = PURPOSE_GDPR_NOTICE) -> SalesCompliancePipelineBinding:
    template = build_template_metadata(
        template_id="tpl_test",
        template_version="1",
        module_owner="sales",
        communication_domain="sales",
        communication_purpose=purpose,
        supported_channels=["email"],
        supported_locales=["pl"],
        lifecycle_status="active",
        policy_version=POLICY_VERSION,
    )
    return SalesCompliancePipelineBinding(
        thread_id="thread-1",
        sales_inquiry_id="si-1",
        communication_purpose=purpose,
        template=template,
        locale="pl",
    )


@pytest.mark.asyncio
async def test_sales_rodo_uses_prepare_and_send_not_smtp() -> None:
    from backend.app.services.lead_rodo import _send_lead_rodo_via_sales_pipeline

    lead = SimpleNamespace(
        id="lead-1",
        own_company_id="oc-1",
        normalized={"email": "a@b.test", "first_name": "Ada"},
    )
    db = AsyncMock()
    db.flush = AsyncMock()

    auth = MagicMock()
    auth.allowed = True
    auth.reason_code = None
    auth.to_dict = MagicMock(return_value={"allowed": True})

    with (
        patch(
            "backend.app.modules.sales.communication.compliance_pipeline"
            ".ensure_sales_compliance_pipeline_binding",
            new_callable=AsyncMock,
            return_value=_binding(),
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
        ok, msg = await _send_lead_rodo_via_sales_pipeline(
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
            ingest_source=None,
            first_name="Ada",
        )

    assert ok is True
    assert "sent" in msg.lower()
    prep.assert_awaited_once()
    smtp.assert_not_called()
    assert lead.normalized["rodo"]["delivery"] == "communication_pipeline"
    assert lead.normalized["rodo"]["status"] == "sent"


@pytest.mark.asyncio
async def test_sales_ops_auto_bind_then_pipeline_send() -> None:
    from backend.app.services.lead_communications import maybe_send_lead_communication

    lead = SimpleNamespace(
        id="lead-1",
        own_company_id="oc-1",
        normalized={
            "email": "ops@b.test",
            "first_name": "Ops",
            "intake_result_link_v1": {
                "result_type": "sales_inquiry",
                "sales_inquiry_id": "si-1",
            },
        },
    )
    db = AsyncMock()
    db.flush = AsyncMock()

    auth = MagicMock()
    auth.allowed = True
    auth.reason_code = None
    auth.to_dict = MagicMock(return_value={"allowed": True})

    cfg = SimpleNamespace(
        enabled=True,
        send_application_received=True,
        send_rejection_notice=True,
        send_moving_forward_notice=True,
        application_received_subject=None,
        application_received_body=None,
        rejection_notice_subject=None,
        rejection_notice_body=None,
        moving_forward_subject=None,
        moving_forward_body=None,
        application_received_template_id=None,
        rejection_notice_template_id=None,
        moving_forward_template_id=None,
    )

    with (
        patch(
            "backend.app.services.lead_communications.get_lead_communication_settings",
            new_callable=AsyncMock,
            return_value=cfg,
        ),
        patch(
            "backend.app.modules.sales.communication.compliance_pipeline"
            ".resolve_lead_uses_sales_compliance_pipeline",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "backend.app.modules.sales.communication.compliance_pipeline"
            ".ensure_sales_compliance_pipeline_binding",
            new_callable=AsyncMock,
            return_value=_binding(purpose=PURPOSE_SUBMISSION_ACK),
        ) as ensure,
        patch(
            "backend.app.communications.send_pipeline.authorize_outbound_communication",
            new_callable=AsyncMock,
            return_value=auth,
        ),
        patch(
            "backend.app.services.lead_communications.resolve_lead_email_message",
            new_callable=AsyncMock,
            return_value=SimpleNamespace(subject="Got it", body="Thanks"),
        ),
        patch(
            "backend.app.communications.prepare_send.prepare_and_send_communication",
            new_callable=AsyncMock,
        ) as prep,
        patch(
            "backend.app.services.lead_communications.log_audit_event",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.app.services.lead_communications.send_email_for_tenant",
            new_callable=AsyncMock,
        ) as smtp,
        patch(
            "backend.app.services.lead_communications.flag_modified",
        ),
    ):
        sent = await maybe_send_lead_communication(
            db,
            tenant_id="t1",
            lead=lead,
            event_type="application_received",
        )

    assert sent is True
    ensure.assert_awaited_once()
    prep.assert_awaited_once()
    smtp.assert_not_called()
