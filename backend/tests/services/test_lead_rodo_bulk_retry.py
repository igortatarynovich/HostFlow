"""Bulk art.14 RODO retry (ADR-031 cutover ops)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.services.lead_rodo_bulk_retry import bulk_retry_lead_rodo


@pytest.mark.asyncio
async def test_bulk_retry_dry_run_lists_failed_only() -> None:
    failed = SimpleNamespace(
        id="lead-failed",
        tenant_id="t1",
        status="new",
        created_at=None,
        normalized={"email": "a@b.test", "rodo": {"status": "failed", "failure_reason": "x"}},
    )
    sent = SimpleNamespace(
        id="lead-sent",
        tenant_id="t1",
        status="new",
        created_at=None,
        normalized={"email": "b@b.test", "rodo": {"status": "sent", "sent_at": "2026-01-01"}},
    )
    db = AsyncMock()
    result_proxy = AsyncMock()
    result_proxy.scalars = lambda: SimpleNamespace(all=lambda: [failed, sent])
    db.execute = AsyncMock(return_value=result_proxy)

    with patch(
        "backend.app.services.lead_rodo_bulk_retry.get_lead_rodo_settings",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(channels=("email",), template_id=None, message_template_id=None),
    ):
        out = await bulk_retry_lead_rodo(
            db,
            tenant_id="t1",
            dry_run=True,
            max_items=10,
        )

    assert out.dry_run is True
    assert out.attempted == 1
    assert out.items[0].lead_id == "lead-failed"
    assert out.items[0].outcome == "dry_run"


@pytest.mark.asyncio
async def test_bulk_retry_calls_send_and_counts_sent() -> None:
    lead = SimpleNamespace(
        id="lead-1",
        tenant_id="t1",
        status="new",
        created_at=None,
        normalized={"email": "a@b.test", "rodo": {"status": "failed"}},
    )
    db = AsyncMock()
    result_proxy = AsyncMock()
    result_proxy.scalars = lambda: SimpleNamespace(all=lambda: [lead])
    db.execute = AsyncMock(return_value=result_proxy)

    async def _send(_db, **kwargs):
        lead.normalized = {
            "email": "a@b.test",
            "rodo": {"status": "sent", "delivery": "communication_pipeline"},
        }
        return True, "RODO email sent for lead"

    with (
        patch(
            "backend.app.services.lead_rodo_bulk_retry.get_lead_rodo_settings",
            new_callable=AsyncMock,
            return_value=SimpleNamespace(channels=("email",), template_id=None, message_template_id=None),
        ),
        patch(
            "backend.app.services.lead_rodo_bulk_retry.send_lead_rodo_email",
            new_callable=AsyncMock,
            side_effect=_send,
        ) as send,
    ):
        out = await bulk_retry_lead_rodo(db, tenant_id="t1", max_items=5)

    send.assert_awaited_once()
    assert out.sent == 1
    assert out.failed == 0
    assert out.items[0].outcome == "sent"
    assert out.items[0].rodo_status_after == "sent"


@pytest.mark.asyncio
async def test_bulk_retry_rejects_unknown_status() -> None:
    db = AsyncMock()
    with pytest.raises(ValueError, match="unsupported"):
        await bulk_retry_lead_rodo(db, tenant_id="t1", statuses=["bogus"])
