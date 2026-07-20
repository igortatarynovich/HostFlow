"""Dispatch freeform fill uses confirmed Thread Result Link module."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.api.v1.communications.routes import dispatch as dispatch_mod
from backend.app.api.v1.communications.schemas import CommunicationDispatchRequest
from backend.app.communications.context_resolver import (
    CommunicationContext,
    CommunicationContextResolveError,
)
from backend.app.communications.manual_thread_reply import PURPOSE_MANUAL_THREAD_REPLY
from backend.app.communications.policy_contract import allow
from backend.app.communications.send_pipeline import CommunicationSendAuthorization
from backend.app.modules.sales.communication.manual_thread_reply import (
    sales_manual_thread_reply_template_metadata,
)


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


@pytest.mark.asyncio
async def test_freeform_dispatch_fills_manual_thread_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thread = SimpleNamespace(id="th-1", channel="email")
    msg = SimpleNamespace(
        direction="outbound",
        is_internal_note=False,
        channel="email",
        payload={},
    )
    body = CommunicationDispatchRequest(mark_delivered=True)

    monkeypatch.setattr(
        dispatch_mod,
        "resolve_communication_context",
        AsyncMock(return_value=_sales_ctx()),
    )

    captured: dict = {}

    async def _auth(_db, request):  # noqa: ANN001
        captured["purpose"] = request.communication_purpose
        captured["template"] = request.template
        return CommunicationSendAuthorization(
            allowed=True,
            reason_code="authorized",
            context=_sales_ctx(),
            policy=allow(
                policy_owner="sales",
                policy_version="sales.communication_policy.v1",
            ),
            template_decision=None,
            authorization_id="auth-1",
        )

    monkeypatch.setattr(dispatch_mod, "authorize_outbound_communication", _auth)

    reason = await dispatch_mod._authorize_outbound_or_reason(
        MagicMock(),
        tenant_id="t1",
        thread=thread,
        msg=msg,
        body=body,
    )
    assert reason is None
    assert captured["purpose"] == PURPOSE_MANUAL_THREAD_REPLY
    assert captured["template"].template_id == sales_manual_thread_reply_template_metadata().template_id
    assert msg.payload.get("communication_purpose") == PURPOSE_MANUAL_THREAD_REPLY
    assert isinstance(msg.payload.get("template_metadata_v1"), dict)


@pytest.mark.asyncio
async def test_freeform_dispatch_surfaces_missing_result_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thread = SimpleNamespace(id="th-1", channel="email")
    msg = SimpleNamespace(
        direction="outbound",
        is_internal_note=False,
        channel="email",
        payload={},
    )
    body = CommunicationDispatchRequest(mark_delivered=True)

    async def _boom(*_a, **_k):  # noqa: ANN002, ANN003
        raise CommunicationContextResolveError(
            "unlinked",
            details={"reason": "missing_result_link"},
        )

    monkeypatch.setattr(dispatch_mod, "resolve_communication_context", _boom)

    reason = await dispatch_mod._authorize_outbound_or_reason(
        MagicMock(),
        tenant_id="t1",
        thread=thread,
        msg=msg,
        body=body,
    )
    assert reason == "missing_result_link"
