"""C2.1 PR-3 — Template Registry SoT (Intent / Channel / Capability)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from backend.app.communications.templates import (
    create_template_with_draft,
    is_template_allowed,
    list_templates_for_capability,
    list_templates_for_channel,
    list_templates_for_intent,
    publish_draft,
)

REGISTRY_PATH = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "communications"
    / "templates"
    / "registry.py"
)

FORBIDDEN_MODULE_PREFIXES = (
    "backend.app.modules.recruitment",
    "backend.app.modules.sales",
    "backend.app.modules.hr",
    "backend.app.modules.services",
    "backend.app.modules.finance",
)


def test_registry_capability_isolation():
    tree = ast.parse(REGISTRY_PATH.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        mods: list[str] = []
        if isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
        if isinstance(node, ast.Import):
            mods.extend(a.name for a in node.names)
        for mod in mods:
            if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_MODULE_PREFIXES):
                offenders.append(mod)
    assert offenders == []


@pytest.mark.asyncio
async def test_registry_lists_and_allow_decision(db, tenant_id: str):
    # Custom intent (not in seed allowlist) → durable bindings are SoT.
    intent = "c2_1_registry_demo_intent"
    template, _draft = await create_template_with_draft(
        db,
        tenant_id=tenant_id,
        key="c2_1_reg_invite",
        name="Registry Invite",
        subject="Hi {{name}}",
        body_text="Hello",
        channels=["email"],
        intent_keys=[intent],
        variables=[{"name": "name", "var_type": "string", "required": True}],
    )
    published = await publish_draft(
        db, tenant_id=tenant_id, template_id=str(template.id)
    )

    # Second template on whatsapp only — must not appear for email.
    t2, _ = await create_template_with_draft(
        db,
        tenant_id=tenant_id,
        key="c2_1_reg_wa",
        name="WA only",
        channels=["whatsapp"],
        intent_keys=[intent],
    )
    await publish_draft(db, tenant_id=tenant_id, template_id=str(t2.id))

    by_intent = await list_templates_for_intent(
        db, tenant_id=tenant_id, intent_key=intent, channel="email"
    )
    keys = {e.template_key for e in by_intent}
    assert keys == {"c2_1_reg_invite"}
    assert by_intent[0].template_version_id == str(published.id)

    by_channel = await list_templates_for_channel(
        db, tenant_id=tenant_id, channel="email", intent_key=intent
    )
    assert {e.template_key for e in by_channel} == {"c2_1_reg_invite"}

    by_cap = await list_templates_for_capability(
        db, tenant_id=tenant_id, capability="email", intent_key=intent
    )
    assert {e.template_key for e in by_cap} == {"c2_1_reg_invite"}

    ok = await is_template_allowed(
        db,
        tenant_id=tenant_id,
        template_key="c2_1_reg_invite",
        intent_key=intent,
        channel="email",
        capability="email",
    )
    assert ok.allowed is True
    assert ok.template_version_id == str(published.id)

    deny_channel = await is_template_allowed(
        db,
        tenant_id=tenant_id,
        template_key="c2_1_reg_invite",
        intent_key=intent,
        channel="whatsapp",
    )
    assert deny_channel.allowed is False
    assert deny_channel.reason_code == "channel_not_bound"

    deny_intent = await is_template_allowed(
        db,
        tenant_id=tenant_id,
        template_key="c2_1_reg_invite",
        intent_key="other_intent",
        channel="email",
    )
    assert deny_intent.allowed is False
    assert deny_intent.reason_code == "intent_not_bound"


@pytest.mark.asyncio
async def test_registry_respects_intent_seed_allowlist(db, tenant_id: str):
    """request_questionnaire seed allowlist only permits questionnaire_invite_email_v1."""
    template, _ = await create_template_with_draft(
        db,
        tenant_id=tenant_id,
        key="not_the_seed_key",
        name="Other",
        channels=["email"],
        intent_keys=["request_questionnaire"],
    )
    await publish_draft(db, tenant_id=tenant_id, template_id=str(template.id))

    listed = await list_templates_for_intent(
        db,
        tenant_id=tenant_id,
        intent_key="request_questionnaire",
        channel="email",
    )
    assert all(e.template_key != "not_the_seed_key" for e in listed)

    decision = await is_template_allowed(
        db,
        tenant_id=tenant_id,
        template_key="not_the_seed_key",
        intent_key="request_questionnaire",
        channel="email",
    )
    assert decision.allowed is False
    assert decision.reason_code == "intent_seed_deny"
