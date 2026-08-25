"""C5 — Communication Send Pipeline (sole outbound entry) + INV-17 guards."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.communications.context_resolver import (
    CommunicationContext,
    CommunicationContextResolveError,
)
from backend.app.communications.policy_contract import allow, deny
from backend.app.communications.send_pipeline import (
    CommunicationSendRequest,
    authorize_outbound_communication,
    send_via_communication_pipeline,
    template_metadata_from_mapping,
)
from backend.app.communications.template_metadata import build_template_metadata


ROOT = Path(__file__).resolve().parents[2] / "app"
COMMS = ROOT / "communications"
MODULES = ROOT / "modules"


def _sales_ctx() -> CommunicationContext:
    return CommunicationContext(
        thread_id="th-1",
        module_owner="sales",
        result_type="sales_inquiry",
        result_id="si-1",
        communication_domain="sales",
        resolution_status="resolved",
        result_link_id="link-1",
        provenance_ledger_id="lg-1",
        resolved_at=datetime.now(timezone.utc),
        resolver_version="communication.context_resolver.v1",
    )


def _sales_template(**overrides):  # noqa: ANN003
    base = dict(
        template_id="tpl_sales_questionnaire_v1",
        template_version="1",
        module_owner="sales",
        communication_domain="sales",
        communication_purpose="qualification_questionnaire_request",
        supported_channels=["email"],
        supported_locales=["pl", "en"],
        lifecycle_status="active",
        policy_version="sales.communication_policy.v1",
    )
    base.update(overrides)
    return build_template_metadata(**base)


def test_c5_pipeline_does_not_import_destination_orm() -> None:
    forbidden = (
        "backend.app.models.sales_inquiry",
        "backend.app.models.recruitment_application",
        "backend.app.modules.sales.services",
        "backend.app.modules.recruitment.services",
    )
    text = (COMMS / "send_pipeline.py").read_text(encoding="utf-8")
    for pattern in forbidden:
        assert pattern not in text


def test_c5_pipeline_does_not_select_templates() -> None:
    text = (COMMS / "send_pipeline.py").read_text(encoding="utf-8")
    assert "Does not send" in text or "authorize" in text
    # No catalog / locale fallback selection in the pipeline entry.
    assert "resolve_template(" not in text
    assert "pick_template" not in text


def test_inv17_destination_modules_must_not_import_transports() -> None:
    """INV-17: Recruitment/Sales must not call transport helpers directly."""
    forbidden_snippets = (
        "send_email_for_tenant",
        "send_email_smtp",
        "send_whatsapp_text",
        "from backend.app.services.tenant_email",
        "from backend.app.services.communications_whatsapp",
        "from backend.app.services.communications_telegram",
    )
    for module_dir in (MODULES / "recruitment", MODULES / "sales"):
        for path in module_dir.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for snippet in forbidden_snippets:
                assert snippet not in text, f"{path}: forbidden transport import {snippet!r}"


def test_inv17_dispatch_route_requires_pipeline_authorize() -> None:
    dispatch = (
        ROOT / "api" / "v1" / "communications" / "routes" / "dispatch.py"
    ).read_text(encoding="utf-8")
    assert "authorize_outbound_communication" in dispatch
    assert "_authorize_outbound_or_reason" in dispatch
    assert "send_pipeline" in dispatch


def test_template_metadata_from_mapping_roundtrip() -> None:
    raw = {
        "template_id": "tpl_x",
        "template_version": "1",
        "module_owner": "sales",
        "communication_domain": "sales",
        "communication_purpose": "qualification_questionnaire_request",
        "supported_channels": ["email"],
        "supported_locales": ["pl"],
        "lifecycle_status": "active",
        "policy_version": "sales.communication_policy.v1",
    }
    meta = template_metadata_from_mapping(raw)
    assert meta is not None
    assert meta.template_id == "tpl_x"
    assert meta.module_owner == "sales"


@pytest.mark.asyncio
async def test_authorize_denied_when_context_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.app.communications.send_pipeline as sp

    async def _boom(*_a, **_k):  # noqa: ANN002, ANN003
        raise CommunicationContextResolveError(
            "unresolved",
            details={"reason": "result_link_missing"},
        )

    monkeypatch.setattr(sp, "resolve_communication_context", _boom)
    auth = await authorize_outbound_communication(
        MagicMock(),
        CommunicationSendRequest(
            tenant_id="t1",
            thread_id="th-1",
            channel="email",
            communication_purpose="qualification_questionnaire_request",
            template=_sales_template(),
        ),
    )
    assert auth.allowed is False
    assert auth.reason_code == "result_link_missing"


@pytest.mark.asyncio
async def test_authorize_denied_when_policy_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.app.communications.send_pipeline as sp

    monkeypatch.setattr(
        sp,
        "resolve_communication_context",
        AsyncMock(return_value=_sales_ctx()),
    )
    monkeypatch.setattr(
        sp,
        "evaluate_policy_for_context",
        lambda *a, **k: deny(  # noqa: ANN002, ANN003
            reason_code="purpose_not_allowed",
            policy_owner="sales",
            policy_version="sales.communication_policy.v1",
        ),
    )
    auth = await authorize_outbound_communication(
        MagicMock(),
        CommunicationSendRequest(
            tenant_id="t1",
            thread_id="th-1",
            channel="email",
            communication_purpose="qualification_questionnaire_request",
            template=_sales_template(),
        ),
    )
    assert auth.allowed is False
    assert auth.reason_code == "purpose_not_allowed"


@pytest.mark.asyncio
async def test_send_invokes_transport_only_after_authorize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.app.communications.send_pipeline as sp

    monkeypatch.setattr(
        sp,
        "resolve_communication_context",
        AsyncMock(return_value=_sales_ctx()),
    )
    monkeypatch.setattr(
        sp,
        "evaluate_policy_for_context",
        lambda *a, **k: allow(  # noqa: ANN002, ANN003
            policy_owner="sales",
            policy_version="sales.communication_policy.v1",
        ),
    )
    called = {"n": 0}

    async def _transport():
        called["n"] += 1
        return "provider-ref-1"

    result = await send_via_communication_pipeline(
        MagicMock(),
        CommunicationSendRequest(
            tenant_id="t1",
            thread_id="th-1",
            channel="email",
            communication_purpose="qualification_questionnaire_request",
            template=_sales_template(),
            locale="pl",
        ),
        transport=_transport,
    )
    assert result.status == "sent"
    assert result.provider_ref == "provider-ref-1"
    assert called["n"] == 1


@pytest.mark.asyncio
async def test_send_does_not_invoke_transport_when_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.app.communications.send_pipeline as sp

    monkeypatch.setattr(
        sp,
        "resolve_communication_context",
        AsyncMock(return_value=_sales_ctx()),
    )
    monkeypatch.setattr(
        sp,
        "evaluate_policy_for_context",
        lambda *a, **k: deny(  # noqa: ANN002, ANN003
            reason_code="purpose_not_allowed",
            policy_owner="sales",
            policy_version="sales.communication_policy.v1",
        ),
    )
    called = {"n": 0}

    async def _transport():
        called["n"] += 1
        return "x"

    result = await send_via_communication_pipeline(
        MagicMock(),
        CommunicationSendRequest(
            tenant_id="t1",
            thread_id="th-1",
            channel="email",
            communication_purpose="recruitment_submission_acknowledgement",
            template=_sales_template(),
        ),
        transport=_transport,
    )
    assert result.status == "denied"
    assert called["n"] == 0
