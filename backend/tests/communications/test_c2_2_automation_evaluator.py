"""C2.2 PR-2 — Pure Rule Evaluator contract tests."""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.communications.automation.evaluator import (
    OUTCOME_FIRE,
    OUTCOME_SKIP,
    EventPayload,
    dry_run,
    evaluate,
)
from backend.app.communications.automation.evaluator.types import (
    DIAG_CONDITIONS_UNMATCHED,
    DIAG_INVALID_CONDITIONS,
    DIAG_RULE_DISABLED,
    DIAG_RULE_NOT_PUBLISHED,
    DIAG_TRIGGER_FILTER_MISMATCH,
    DIAG_TRIGGER_MISMATCH,
)
from backend.app.communications.automation.payload import build_rule_payload

EVALUATOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "communications"
    / "automation"
    / "evaluator"
)

FORBIDDEN_IMPORT_PREFIXES = (
    "sqlalchemy",
    "backend.app.db",
    "app.db",
    "backend.app.models",
    "app.models",
    "backend.app.communications.workspace_commands",
    "backend.app.communications.send_communication",
    "backend.app.communications.execute_intent",
    "backend.app.communications.templates",
    "backend.app.modules",
    "app.modules",
)


def _published_rule(**overrides):
    base = dict(
        rule_id="rule-1",
        rule_version_id="ver-1",
        version_status="published",
        rule_status="active",
        enabled=True,
        intent_key="follow_up",
        preferred_template_key="follow_up_email",
        channel="email",
        recipient_strategy="origin_primary",
        recipient_config={},
        conditions={"op": "eq", "path": "stage", "value": "interview"},
        variables_mapping={
            "contact_name": "candidate.name",
            "locale": {"literal": "pl"},
        },
        triggers=[("candidate.stage_changed", {})],
    )
    base.update(overrides)
    return build_rule_payload(**base)


def _event(**overrides) -> EventPayload:
    base = dict(
        event_id="evt-1",
        event_type="candidate.stage_changed",
        data={"stage": "interview", "candidate": {"name": "Ada"}},
        correlation_id="corr-1",
    )
    base.update(overrides)
    return EventPayload(**base)


def test_pure_evaluator_import_gate():
    offenders: list[str] = []
    for path in EVALUATOR_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
            if isinstance(node, ast.Import):
                mods.extend(a.name for a in node.names)
            for mod in mods:
                if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_IMPORT_PREFIXES):
                    offenders.append(f"{path.name}: {mod}")
    assert offenders == [], f"Pure evaluator gate violated: {offenders}"


def test_evaluate_fire_deterministic_and_maps_variables():
    rule = _published_rule()
    event = _event()
    r1 = evaluate(rule, event)
    r2 = evaluate(rule, event)
    d1 = dry_run(rule, event)
    assert r1.ok is True
    assert r1.outcome == OUTCOME_FIRE
    assert r1.intent_key == "follow_up"
    assert r1.preferred_template_key == "follow_up_email"
    assert r1.template_variables == {"contact_name": "Ada", "locale": "pl"}
    assert r1.reason_codes == ("matched",)
    assert r1 == r2
    assert r1 == d1
    assert r1.to_dict() == r2.to_dict()


def test_skip_reasons_and_invalid_conditions():
    rule = _published_rule()
    skip_stage = evaluate(rule, _event(data={"stage": "hired", "candidate": {"name": "Ada"}}))
    assert skip_stage.outcome == OUTCOME_SKIP
    assert DIAG_CONDITIONS_UNMATCHED in skip_stage.reason_codes

    skip_trigger = evaluate(rule, _event(event_type="lead.created"))
    assert DIAG_TRIGGER_MISMATCH in skip_trigger.reason_codes

    filtered = _published_rule(triggers=[("candidate.stage_changed", {"source": "manual"})])
    skip_filter = evaluate(filtered, _event())
    assert DIAG_TRIGGER_FILTER_MISMATCH in skip_filter.reason_codes

    draft = _published_rule(version_status="draft")
    skip_draft = evaluate(draft, _event())
    assert DIAG_RULE_NOT_PUBLISHED in skip_draft.reason_codes

    disabled = _published_rule(enabled=False)
    skip_disabled = evaluate(disabled, _event())
    assert DIAG_RULE_DISABLED in skip_disabled.reason_codes

    bad = _published_rule(conditions={"op": "unknown_op", "path": "x", "value": 1})
    bad_result = evaluate(bad, _event())
    assert bad_result.ok is False
    assert DIAG_INVALID_CONDITIONS in bad_result.reason_codes


def test_and_or_not_conditions():
    rule = _published_rule(
        conditions={
            "op": "and",
            "args": [
                {"op": "eq", "path": "stage", "value": "interview"},
                {
                    "op": "or",
                    "args": [
                        {"op": "eq", "path": "channel", "value": "email"},
                        {"op": "eq", "path": "channel", "value": "sms"},
                    ],
                },
                {"op": "not", "arg": {"op": "eq", "path": "blocked", "value": True}},
            ],
        }
    )
    fire = evaluate(
        rule,
        _event(data={"stage": "interview", "channel": "email", "blocked": False}),
    )
    assert fire.outcome == OUTCOME_FIRE

    skip = evaluate(
        rule,
        _event(data={"stage": "interview", "channel": "telegram", "blocked": False}),
    )
    assert skip.outcome == OUTCOME_SKIP


def test_empty_conditions_match_all():
    rule = _published_rule(conditions={})
    result = evaluate(rule, _event(data={"anything": 1}))
    assert result.outcome == OUTCOME_FIRE
