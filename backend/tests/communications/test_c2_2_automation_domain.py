"""C2.2 PR-1 — Automation domain invariants (no UI / no evaluator / no send)."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.communications.automation import (
    AutomationDomainError,
    create_rule_with_draft,
    get_draft_version,
    publish_draft,
    record_decision,
    replace_draft_triggers,
    update_draft_content,
)
from backend.app.communications.automation.lifecycle import assert_version_immutable_for_write
from backend.app.models.communication_automation import (
    DECISION_OUTCOME_FIRE,
    DECISION_OUTCOME_SKIP,
    VERSION_STATUS_DRAFT,
    VERSION_STATUS_PUBLISHED,
    CommunicationAutomationDecision,
    CommunicationAutomationRuleVersion,
)

REPO = Path(__file__).resolve().parents[2]
AUTOMATION_PKG = REPO / "app" / "communications" / "automation"
AUTOMATION_MODEL = REPO / "app" / "models" / "communication_automation.py"

FORBIDDEN_MODULE_IMPORT_PREFIXES = (
    "backend.app.modules.recruitment",
    "backend.app.modules.sales",
    "backend.app.modules.hr",
    "backend.app.modules.services",
    "backend.app.modules.finance",
    "app.modules.recruitment",
    "app.modules.sales",
    "app.modules.hr",
    "app.modules.services",
    "app.modules.finance",
)

FORBIDDEN_SEND_PATH_TOKENS = (
    "CommunicationSender",
    "execute_communication_intent",
    "dispatch_message",
    "send_email",
)


def _iter_py_files(root: Path):
    if root.is_file():
        yield root
        return
    for path in root.rglob("*.py"):
        yield path


def test_capability_isolation_no_module_imports():
    offenders: list[str] = []
    for path in (*_iter_py_files(AUTOMATION_PKG), AUTOMATION_MODEL):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_MODULE_IMPORT_PREFIXES):
                    offenders.append(f"{path.name}: from {mod}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if any(
                        name == p or name.startswith(p + ".")
                        for p in FORBIDDEN_MODULE_IMPORT_PREFIXES
                    ):
                        offenders.append(f"{path.name}: import {name}")
        for token in FORBIDDEN_SEND_PATH_TOKENS:
            if token in text:
                offenders.append(f"{path.name}: token:{token}")
    assert offenders == [], f"C2.2 capability isolation violated: {offenders}"


def test_orm_names_do_not_collide_with_legacy_automation_rule_table():
    text = AUTOMATION_MODEL.read_text(encoding="utf-8")
    assert '__tablename__ = "communication_automation_rules"' in text
    assert '__tablename__ = "automation_rules"' not in text


@pytest.mark.asyncio
async def test_publish_creates_immutable_version_and_keeps_draft(db, tenant_id: str):
    rule, draft = await create_rule_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_2_smoke_{uuid4().hex[:8]}",
        name="C2.2 Smoke Rule",
        intent_key="follow_up",
        preferred_template_key="follow_up_email",
        channel="email",
        event_types=["candidate.stage_changed"],
        conditions={"op": "eq", "path": "stage", "value": "interview"},
    )
    assert draft.status == VERSION_STATUS_DRAFT
    assert draft.version_number == 0
    assert len(draft.triggers or []) == 1

    published = await publish_draft(
        db,
        tenant_id=tenant_id,
        rule_id=str(rule.id),
        actor_user_id="actor-1",
    )
    assert published.status == VERSION_STATUS_PUBLISHED
    assert published.version_number == 1
    assert published.id != draft.id
    assert published.intent_key == "follow_up"
    assert published.published_at is not None
    assert len(published.triggers or []) == 1

    draft2 = await get_draft_version(db, tenant_id=tenant_id, rule_id=str(rule.id))
    assert draft2.id == draft.id
    await update_draft_content(
        db,
        tenant_id=tenant_id,
        version=draft2,
        intent_key="manual_outbound",
    )
    assert draft2.intent_key == "manual_outbound"

    with pytest.raises(AutomationDomainError) as exc:
        assert_version_immutable_for_write(published)
    assert exc.value.code == "published_immutable"

    with pytest.raises(AutomationDomainError) as exc2:
        await update_draft_content(
            db,
            tenant_id=tenant_id,
            version=published,
            intent_key="hack",
        )
    assert exc2.value.code == "version_not_draft"

    published2 = await publish_draft(
        db,
        tenant_id=tenant_id,
        rule_id=str(rule.id),
    )
    assert published2.version_number == 2
    assert published2.intent_key == "manual_outbound"

    v1 = (
        await db.execute(
            select(CommunicationAutomationRuleVersion).where(
                CommunicationAutomationRuleVersion.id == published.id
            )
        )
    ).scalar_one()
    assert v1.intent_key == "follow_up"
    assert v1.status == VERSION_STATUS_PUBLISHED


@pytest.mark.asyncio
async def test_cannot_replace_triggers_on_published(db, tenant_id: str):
    rule, _draft = await create_rule_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_2_pub_trig_{uuid4().hex[:8]}",
        name="pub triggers",
        intent_key="follow_up",
        event_types=["lead.created"],
    )
    published = await publish_draft(db, tenant_id=tenant_id, rule_id=str(rule.id))
    with pytest.raises(AutomationDomainError) as exc:
        await replace_draft_triggers(
            db,
            tenant_id=tenant_id,
            version=published,
            event_types=["lead.updated"],
        )
    assert exc.value.code == "version_not_draft"


@pytest.mark.asyncio
async def test_publish_requires_trigger(db, tenant_id: str):
    rule, _draft = await create_rule_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_2_no_trig_{uuid4().hex[:8]}",
        name="no trigger",
        intent_key="follow_up",
    )
    with pytest.raises(AutomationDomainError) as exc:
        await publish_draft(db, tenant_id=tenant_id, rule_id=str(rule.id))
    assert exc.value.code == "trigger_required"


@pytest.mark.asyncio
async def test_record_decision_fire_and_skip(db, tenant_id: str):
    rule, draft = await create_rule_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_2_dec_{uuid4().hex[:8]}",
        name="decision",
        intent_key="follow_up",
        event_types=["candidate.created"],
    )
    published = await publish_draft(db, tenant_id=tenant_id, rule_id=str(rule.id))

    fire = await record_decision(
        db,
        tenant_id=tenant_id,
        rule_id=str(rule.id),
        rule_version_id=str(published.id),
        source_event_id="evt-1",
        event_type="candidate.created",
        outcome=DECISION_OUTCOME_FIRE,
        reason_codes=["matched"],
        intent_key="follow_up",
        intent_request_snapshot={"intent": "follow_up", "channel": "email"},
    )
    skip = await record_decision(
        db,
        tenant_id=tenant_id,
        rule_id=str(rule.id),
        rule_version_id=str(published.id),
        source_event_id="evt-2",
        event_type="candidate.created",
        outcome=DECISION_OUTCOME_SKIP,
        reason_codes=["conditions_unmatched"],
    )
    assert fire.outcome == DECISION_OUTCOME_FIRE
    assert fire.intent_request_snapshot is not None
    assert skip.outcome == DECISION_OUTCOME_SKIP

    rows = (
        await db.execute(
            select(CommunicationAutomationDecision).where(
                CommunicationAutomationDecision.tenant_id == tenant_id,
                CommunicationAutomationDecision.rule_id == str(rule.id),
            )
        )
    ).scalars().all()
    assert len(rows) == 2

    # Draft id unused for fire path — ensure we did not require evaluator.
    assert draft.id != published.id
