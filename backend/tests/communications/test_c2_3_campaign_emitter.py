"""C2.3 PR-3 — Campaign Intent Emitter contract tests."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.communications.campaign import (
    DEFINITION_TYPE_STATIC_LIST,
    CampaignDomainError,
    CampaignEmitContext,
    CampaignItemEmitInput,
    RUN_ITEM_STATUS_EMITTED,
    RUN_ITEM_STATUS_FAILED,
    RUN_ITEM_STATUS_SKIPPED,
    build_intent_request,
    campaign_identity_for,
    create_campaign_with_draft,
    create_run_from_audience,
    emit_run_item,
    emit_run_items,
    get_run,
    publish_draft,
)
from backend.app.communications.send_communication import SendCommunicationError

EMITTER = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "communications"
    / "campaign"
    / "emitter.py"
)

FORBIDDEN_IMPORT_PREFIXES = (
    "backend.app.communications.workspace_commands",
    "backend.app.modules",
    "app.modules",
)

FORBIDDEN_MODEL_PREFIXES = (
    "backend.app.models.communication_thread",
    "backend.app.models.communication_message",
    "app.models.communication_thread",
    "app.models.communication_message",
)

FORBIDDEN_TOKENS = (
    "CommunicationSender",
    "dispatch_message",
    "send_email",
    "CommunicationThread",
)


def _emit_input(**overrides) -> CampaignItemEmitInput:
    base = dict(
        tenant_id="tenant-1",
        campaign_id="camp-1",
        campaign_version_id="ver-1",
        run_id="run-1",
        run_item_id="item-1",
        recipient_id="recip-1",
        intent_key="follow_up",
        preferred_template_key=None,
        channel="email",
        entity_type="candidate",
        entity_id="c-1",
        address="ada@example.com",
        label="Ada",
        template_variables={"name": "Ada"},
    )
    base.update(overrides)
    return CampaignItemEmitInput(**base)


def test_emitter_isolation_gate():
    text = EMITTER.read_text(encoding="utf-8")
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
            if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_MODEL_PREFIXES):
                offenders.append(f"model:{mod}")
            if mod == "backend.app.models.communication" or mod.startswith(
                "backend.app.models.communication."
            ):
                if "communication_campaign" not in mod:
                    offenders.append(f"model:{mod}")
    for token in FORBIDDEN_TOKENS:
        if token in text:
            offenders.append(f"token:{token}")
    assert "execute_communication_intent" in text
    assert offenders == [], f"Emitter isolation violated: {offenders}"


def test_build_intent_request_for_item():
    req = build_intent_request(_emit_input(), CampaignEmitContext(locale="pl"))
    assert req.intent == "follow_up"
    assert req.channel == "email"
    assert req.automation_identity == "comm_campaign:camp-1:ver-1"
    assert req.idempotency_key == "campaign:run-1:item-1"
    assert req.source_event_id == "campaign:run-1:item-1"
    assert req.meta["campaign_run_item_id"] == "item-1"
    assert req.recipients[0].address == "ada@example.com"
    assert req.template_variables["name"] == "Ada"
    assert campaign_identity_for(campaign_id="camp-1", campaign_version_id="ver-1") == (
        "comm_campaign:camp-1:ver-1"
    )


def test_build_intent_request_rejects_missing_address():
    with pytest.raises(CampaignDomainError) as exc:
        build_intent_request(_emit_input(address=""))
    assert exc.value.code == "emit_address_required"


async def _published_run(db, tenant_id: str, *, recipients: list[dict]):
    campaign, _draft = await create_campaign_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_3_emit_{uuid4().hex[:8]}",
        name="emit",
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
        idempotency_key=f"emit-{uuid4().hex}",
    )
    return campaign, published, run


@pytest.mark.asyncio
async def test_emit_request_only_marks_item_emitted(db, tenant_id: str):
    _campaign, _published, run = await _published_run(
        db,
        tenant_id,
        recipients=[
            {
                "entity_type": "candidate",
                "entity_id": "c-1",
                "address": "one@example.com",
                "snapshot": {"name": "One"},
            }
        ],
    )
    item = run.items[0]
    result = await emit_run_item(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        run_item_id=str(item.id),
        mode="request_only",
    )
    assert result.emitted is True
    assert result.intent_request is not None
    assert result.intent_request.automation_identity.startswith("comm_campaign:")
    assert result.execute_result is None
    assert result.item_status == RUN_ITEM_STATUS_EMITTED

    reloaded = await get_run(db, tenant_id=tenant_id, run_id=str(run.id))
    assert reloaded.items[0].status == RUN_ITEM_STATUS_EMITTED
    assert reloaded.items[0].intent_key == "follow_up"
    assert reloaded.items[0].meta["emit_mode"] == "request_only"

    # Idempotent: second emit does not re-fire.
    again = await emit_run_item(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        run_item_id=str(item.id),
        mode="request_only",
    )
    assert again.emitted is False
    assert again.skip_reason == "already_emitted"


@pytest.mark.asyncio
async def test_emit_isolates_item_failures(db, tenant_id: str, monkeypatch):
    _campaign, _published, run = await _published_run(
        db,
        tenant_id,
        recipients=[
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
    items = sorted(run.items, key=lambda i: i.recipient_id)
    bad_item = next(
        i for i in items if i.recipient and i.recipient.entity_id == "bad"
    )
    ok_item = next(i for i in items if i.recipient and i.recipient.entity_id == "ok")

    original = emit_run_item.__wrapped__ if hasattr(emit_run_item, "__wrapped__") else None
    # Patch execute path: fail only for bad recipient via monkeypatch on execute.
    from backend.app.communications.campaign import emitter as emitter_mod

    real_execute = emitter_mod.execute_communication_intent

    async def flaky_execute(db, request, **kwargs):
        if request.origin.entity_id == "bad":
            raise SendCommunicationError(
                "simulated failure",
                details={"reason": "simulated_failure"},
            )
        # request_only path does not call execute; for execute mode of ok item
        # we still want success without full send — use request path in test instead.
        raise AssertionError("execute should not be reached in this test")

    monkeypatch.setattr(emitter_mod, "execute_communication_intent", flaky_execute)

    # Use request_only for the good item by calling emit_run_items with mode request_only
    # and separately verify failure isolation with execute mode on bad only.
    ok_result = await emit_run_item(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        run_item_id=str(ok_item.id),
        mode="request_only",
    )
    assert ok_result.emitted is True

    bad_result = await emit_run_item(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        run_item_id=str(bad_item.id),
        mode="execute",
        skip_transport=True,
    )
    assert bad_result.emitted is False
    assert bad_result.error_code == "simulated_failure"
    assert bad_result.item_status == RUN_ITEM_STATUS_FAILED

    reloaded = await get_run(db, tenant_id=tenant_id, run_id=str(run.id))
    by_id = {i.id: i for i in reloaded.items}
    assert by_id[ok_item.id].status == RUN_ITEM_STATUS_EMITTED
    assert by_id[bad_item.id].status == RUN_ITEM_STATUS_FAILED
    assert by_id[bad_item.id].reason_codes == ["simulated_failure"]
    _ = original
    _ = real_execute


@pytest.mark.asyncio
async def test_emit_run_items_continues_after_one_failure(db, tenant_id: str, monkeypatch):
    _campaign, _published, run = await _published_run(
        db,
        tenant_id,
        recipients=[
            {
                "entity_type": "candidate",
                "entity_id": "a",
                "address": "a@example.com",
            },
            {
                "entity_type": "candidate",
                "entity_id": "b",
                "address": "b@example.com",
            },
        ],
    )
    from backend.app.communications.campaign import emitter as emitter_mod

    calls = {"n": 0}

    async def boom_then_ok(db, request, **kwargs):
        calls["n"] += 1
        if request.origin.entity_id == "a":
            raise SendCommunicationError("boom", details={"reason": "boom"})
        # Second item: don't need real execute — raise a different signal?
        # Better: use request_only for batch.
        raise AssertionError("unexpected execute")

    monkeypatch.setattr(emitter_mod, "execute_communication_intent", boom_then_ok)

    # Batch in request_only — both succeed; then verify isolation separately with mixed statuses.
    results = await emit_run_items(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        mode="request_only",
    )
    assert len(results) == 2
    assert all(r.emitted for r in results)

    # Fresh run for execute isolation across emit_run_items
    _c2, _p2, run2 = await _published_run(
        db,
        tenant_id,
        recipients=[
            {
                "entity_type": "candidate",
                "entity_id": "a",
                "address": "a2@example.com",
            },
            {
                "entity_type": "candidate",
                "entity_id": "b",
                "address": "b2@example.com",
            },
        ],
    )

    async def fail_a_only(db, request, **kwargs):
        if request.origin.entity_id == "a":
            raise SendCommunicationError("boom", details={"reason": "boom"})
        # For b: simulate success by returning a simple namespace
        from types import SimpleNamespace

        return SimpleNamespace(message_id="msg-b", delivery_ids=[])

    monkeypatch.setattr(emitter_mod, "execute_communication_intent", fail_a_only)
    batch = await emit_run_items(
        db,
        tenant_id=tenant_id,
        run_id=str(run2.id),
        mode="execute",
        skip_transport=True,
    )
    assert len(batch) == 2
    by_entity = {
        (r.intent_request.origin.entity_id if r.intent_request else None): r for r in batch
    }
    # Sort results by looking at reloaded statuses
    reloaded = await get_run(db, tenant_id=tenant_id, run_id=str(run2.id))
    statuses = {i.recipient.entity_id: i.status for i in reloaded.items}
    assert statuses["a"] == RUN_ITEM_STATUS_FAILED
    assert statuses["b"] == RUN_ITEM_STATUS_EMITTED
    assert any(r.emitted for r in batch)
    assert any(not r.emitted for r in batch)
    _ = by_entity


@pytest.mark.asyncio
async def test_emit_skips_item_without_origin(db, tenant_id: str):
    _campaign, _published, run = await _published_run(
        db,
        tenant_id,
        recipients=[
            {
                "entity_type": "",
                "entity_id": "",
                "address": "x@example.com",
            }
        ],
    )
    item = run.items[0]
    result = await emit_run_item(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        run_item_id=str(item.id),
        mode="request_only",
    )
    assert result.emitted is False
    assert result.item_status == RUN_ITEM_STATUS_SKIPPED
    assert result.skip_reason == "emit_origin_required"
