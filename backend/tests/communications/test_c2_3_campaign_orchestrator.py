"""C2.3 PR-4 — Campaign Run Orchestration contract tests."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.app.communications.campaign import (
    CAMPAIGN_RUN_STATUS_CANCELLED,
    CAMPAIGN_RUN_STATUS_COMPLETED,
    CAMPAIGN_RUN_STATUS_PENDING,
    DEFINITION_TYPE_STATIC_LIST,
    RUN_ITEM_STATUS_EMITTED,
    RUN_ITEM_STATUS_FAILED,
    CampaignDomainError,
    cancel_campaign_run,
    create_campaign_with_draft,
    create_run_from_audience,
    execute_campaign_run,
    get_run,
    publish_draft,
)
from backend.app.communications.send_communication import SendCommunicationError

ORCHESTRATOR = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "communications"
    / "campaign"
    / "orchestrator.py"
)

FORBIDDEN_IMPORT_PREFIXES = (
    "backend.app.communications.workspace_commands",
    "backend.app.modules",
    "app.modules",
)

FORBIDDEN_TOKENS = (
    "CommunicationSender",
    "dispatch_message",
    "send_email",
    "CommunicationThread",
    "execute_communication_intent",
)


def test_orchestrator_isolation_gate():
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    tree = ast.parse(text)
    offenders: list[str] = []
    for node in ast.walk(tree):
        mods: list[str] = []
        if isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
        if isinstance(node, ast.Import):
            mods.extend(a.name for a in node.names)
        for mod in mods:
            if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_IMPORT_PREFIXES):
                offenders.append(f"import:{mod}")
    for token in FORBIDDEN_TOKENS:
        if token in text:
            offenders.append(f"token:{token}")
    assert "emit_run_items" in text
    assert offenders == [], f"Orchestrator isolation violated: {offenders}"


async def _run_with_recipients(db, tenant_id: str, recipients: list[dict]):
    campaign, _draft = await create_campaign_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_3_orch_{uuid4().hex[:8]}",
        name="orch",
        intent_key="follow_up",
        channel="email",
        audience_definition_type=DEFINITION_TYPE_STATIC_LIST,
        audience_definition={"recipients": recipients},
    )
    published = await publish_draft(db, tenant_id=tenant_id, campaign_id=str(campaign.id))
    run = await create_run_from_audience(
        db,
        tenant_id=tenant_id,
        campaign_id=str(campaign.id),
        campaign_version_id=str(published.id),
        idempotency_key=f"orch-{uuid4().hex}",
    )
    assert run.status == CAMPAIGN_RUN_STATUS_PENDING
    return run


@pytest.mark.asyncio
async def test_execute_run_completes_all_items(db, tenant_id: str):
    run = await _run_with_recipients(
        db,
        tenant_id,
        [
            {
                "entity_type": "candidate",
                "entity_id": "1",
                "address": "a@example.com",
            },
            {
                "entity_type": "candidate",
                "entity_id": "2",
                "address": "b@example.com",
            },
        ],
    )
    result = await execute_campaign_run(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        mode="request_only",
    )
    assert result.status == CAMPAIGN_RUN_STATUS_COMPLETED
    assert result.summary.total == 2
    assert result.summary.emitted == 2
    assert result.summary.failed == 0
    assert result.already_terminal is False

    reloaded = await get_run(db, tenant_id=tenant_id, run_id=str(run.id))
    assert reloaded.status == CAMPAIGN_RUN_STATUS_COMPLETED
    assert reloaded.started_at is not None
    assert reloaded.completed_at is not None
    assert all(i.status == RUN_ITEM_STATUS_EMITTED for i in reloaded.items)
    assert reloaded.meta["orchestration"]["summary"]["emitted"] == 2

    # Idempotent re-execute
    again = await execute_campaign_run(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        mode="request_only",
    )
    assert again.already_terminal is True
    assert again.status == CAMPAIGN_RUN_STATUS_COMPLETED


@pytest.mark.asyncio
async def test_execute_run_partial_item_failures_still_completes(
    db, tenant_id: str, monkeypatch
):
    run = await _run_with_recipients(
        db,
        tenant_id,
        [
            {
                "entity_type": "candidate",
                "entity_id": "ok",
                "address": "ok@example.com",
            },
            {
                "entity_type": "candidate",
                "entity_id": "bad",
                "address": "bad@example.com",
            },
        ],
    )
    from backend.app.communications.campaign import emitter as emitter_mod

    async def fail_bad(db, request, **kwargs):
        if request.origin.entity_id == "bad":
            raise SendCommunicationError("boom", details={"reason": "boom"})
        return SimpleNamespace(message_id="msg-ok", delivery_ids=[])

    monkeypatch.setattr(emitter_mod, "execute_communication_intent", fail_bad)

    result = await execute_campaign_run(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        mode="execute",
        skip_transport=True,
    )
    assert result.status == CAMPAIGN_RUN_STATUS_COMPLETED
    assert result.summary.emitted == 1
    assert result.summary.failed == 1

    reloaded = await get_run(db, tenant_id=tenant_id, run_id=str(run.id))
    by_entity = {i.recipient.entity_id: i.status for i in reloaded.items}
    assert by_entity["ok"] == RUN_ITEM_STATUS_EMITTED
    assert by_entity["bad"] == RUN_ITEM_STATUS_FAILED
    assert reloaded.status == CAMPAIGN_RUN_STATUS_COMPLETED


@pytest.mark.asyncio
async def test_cancel_run_blocks_execution(db, tenant_id: str):
    run = await _run_with_recipients(
        db,
        tenant_id,
        [
            {
                "entity_type": "candidate",
                "entity_id": "1",
                "address": "a@example.com",
            }
        ],
    )
    cancelled = await cancel_campaign_run(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        reason="operator_abort",
    )
    assert cancelled.status == CAMPAIGN_RUN_STATUS_CANCELLED

    result = await execute_campaign_run(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        mode="request_only",
    )
    assert result.already_terminal is True
    assert result.status == CAMPAIGN_RUN_STATUS_CANCELLED

    reloaded = await get_run(db, tenant_id=tenant_id, run_id=str(run.id))
    assert all(i.status != RUN_ITEM_STATUS_EMITTED for i in reloaded.items)

    with pytest.raises(CampaignDomainError) as exc:
        await cancel_campaign_run(db, tenant_id=tenant_id, run_id=str(run.id))
    assert exc.value.code == "run_terminal"
