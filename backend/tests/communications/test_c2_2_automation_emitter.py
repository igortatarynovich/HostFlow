"""C2.2 PR-3 — Intent Emitter contract tests."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.communications.automation import (
    AutomationDomainError,
    EmitContext,
    OUTCOME_FIRE,
    OUTCOME_SKIP,
    build_intent_request,
    build_rule_payload,
    emit_from_evaluation,
    evaluate,
)
from backend.app.communications.automation.evaluator.types import EventPayload
from backend.app.communications.command import CommunicationOrigin, CommunicationRecipient
from backend.app.models.communication_automation import CommunicationAutomationDecision
from sqlalchemy import select

EMITTER = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "communications"
    / "automation"
    / "emitter.py"
)

FORBIDDEN_IMPORT_PREFIXES = (
    "backend.app.communications.workspace_commands",
    "backend.app.modules",
    "app.modules",
)

# Thread/Message ORM — allow communication_automation only.
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


def _fire_evaluation(**overrides):
    rule = build_rule_payload(
        rule_id="rule-1",
        rule_version_id="ver-1",
        version_status="published",
        rule_status="active",
        enabled=True,
        intent_key="manual_outbound",
        preferred_template_key=None,
        channel="email",
        recipient_strategy="origin_primary",
        recipient_config={},
        conditions={},
        variables_mapping={"name": {"literal": "Ada"}},
        triggers=[("candidate.created", {})],
    )
    event = EventPayload(
        event_id="evt-1",
        event_type="candidate.created",
        data={},
        correlation_id="corr-1",
    )
    result = evaluate(rule, event)
    assert result.outcome == OUTCOME_FIRE
    # Allow test overrides via replace-like rebuild
    if overrides:
        from dataclasses import replace

        result = replace(result, **overrides)
    return result


def _ctx(tenant_id: str) -> EmitContext:
    return EmitContext(
        tenant_id=tenant_id,
        origin=CommunicationOrigin(entity_type="candidate", entity_id="c-1"),
        recipients=[
            CommunicationRecipient(address="ada@example.com", label="Ada"),
        ],
        locale="pl",
    )


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
                if "communication_automation" not in mod:
                    offenders.append(f"model:{mod}")
    for token in FORBIDDEN_TOKENS:
        if token in text:
            offenders.append(f"token:{token}")
    # Must go through platform Intent path.
    assert "execute_communication_intent" in text
    assert offenders == [], f"Emitter isolation violated: {offenders}"


def test_build_intent_request_from_fire():
    evaluation = _fire_evaluation()
    req = build_intent_request(evaluation, _ctx("tenant-1"))
    assert req.intent == "manual_outbound"
    assert req.channel == "email"
    assert req.automation_identity == "comm_automation:rule-1:ver-1"
    assert req.source_event_id == "evt-1"
    assert req.template_variables.get("name") == "Ada"
    assert req.meta["automation_rule_version_id"] == "ver-1"
    assert req.idempotency_key == "auto:ver-1:evt-1"


def test_build_intent_request_rejects_skip():
    evaluation = _fire_evaluation()
    from dataclasses import replace

    skipped = replace(
        evaluation,
        outcome=OUTCOME_SKIP,
        intent_key=None,
        reason_codes=( "conditions_unmatched",),
    )
    with pytest.raises(AutomationDomainError) as exc:
        build_intent_request(skipped, _ctx("tenant-1"))
    assert exc.value.code == "emit_requires_fire"


@pytest.mark.asyncio
async def test_emit_skip_records_decision_without_intent(db, tenant_id: str):
    evaluation = _fire_evaluation()
    from dataclasses import replace

    skipped = replace(
        evaluation,
        outcome=OUTCOME_SKIP,
        intent_key=None,
        reason_codes=("trigger_mismatch",),
        rule_id=str(uuid4()),
        rule_version_id=str(uuid4()),
        source_event_id=f"evt-{uuid4().hex[:8]}",
    )
    result = await emit_from_evaluation(
        db,
        skipped,
        _ctx(tenant_id),
        mode="request_only",
    )
    assert result.emitted is False
    assert result.intent_request is None
    assert result.decision is not None
    assert result.decision.outcome == OUTCOME_SKIP
    assert result.skip_reason == "trigger_mismatch"


@pytest.mark.asyncio
async def test_emit_fire_request_only_persists_snapshot(db, tenant_id: str):
    evaluation = _fire_evaluation()
    from dataclasses import replace

    evaluation = replace(
        evaluation,
        rule_id=str(uuid4()),
        rule_version_id=str(uuid4()),
        source_event_id=f"evt-{uuid4().hex[:8]}",
    )
    result = await emit_from_evaluation(
        db,
        evaluation,
        _ctx(tenant_id),
        mode="request_only",
    )
    assert result.emitted is True
    assert result.intent_request is not None
    assert result.intent_request.automation_identity.startswith("comm_automation:")
    assert result.decision is not None
    assert result.decision.outcome == OUTCOME_FIRE
    assert result.decision.intent_request_snapshot is not None
    assert result.decision.intent_request_snapshot["intent"] == "manual_outbound"
    assert result.execute_result is None

    rows = (
        await db.execute(
            select(CommunicationAutomationDecision).where(
                CommunicationAutomationDecision.id == result.decision.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
