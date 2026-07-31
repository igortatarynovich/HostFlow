"""Lead timeline always surfaces arrival even without ActivityLog ingest rows."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.modules.leads.service._timeline import get_lead_timeline


@pytest.mark.asyncio
async def test_timeline_includes_synthetic_lead_received_when_no_activity() -> None:
    created = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    lead = SimpleNamespace(
        id="lead-1",
        tenant_id="t1",
        created_at=created,
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
    )

    lead_result = MagicMock()
    lead_result.scalar_one_or_none.return_value = lead

    empty_logs = MagicMock()
    empty_logs.all.return_value = []

    empty_rems = MagicMock()
    empty_rems.all.return_value = []

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[lead_result, empty_logs, empty_rems])

    out = await get_lead_timeline(db, tenant_id="t1", lead_id="lead-1")
    assert len(out.items) == 1
    ev = out.items[0]
    assert ev.kind == "lead_received"
    assert ev.title == "lead.received"
    assert ev.description == "meta"
    assert ev.at == created
    assert ev.payload.get("synthetic") is True


@pytest.mark.asyncio
async def test_timeline_skips_synthetic_when_lead_created_logged() -> None:
    created = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    lead = SimpleNamespace(
        id="lead-1",
        tenant_id="t1",
        created_at=created,
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
    )

    lead_result = MagicMock()
    lead_result.scalar_one_or_none.return_value = lead

    log_rows = MagicMock()
    log_rows.all.return_value = [
        ("lead.created", created, {"source": "meta"}),
    ]

    empty_rems = MagicMock()
    empty_rems.all.return_value = []

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[lead_result, log_rows, empty_rems])

    out = await get_lead_timeline(db, tenant_id="t1", lead_id="lead-1")
    received = [e for e in out.items if e.kind == "lead_received"]
    assert len(received) == 1
    assert received[0].payload.get("synthetic") is not True
