"""ORM → pure RuleVersionPayload adapter (outside evaluator; may use ORM)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from backend.app.communications.automation.evaluator.types import (
    RuleVersionPayload,
    TriggerSpec,
)
from backend.app.models.communication_automation import (
    CommunicationAutomationRule,
    CommunicationAutomationRuleVersion,
)


def build_rule_payload(
    *,
    rule_id: str,
    rule_version_id: str,
    version_status: str,
    rule_status: str,
    enabled: bool,
    intent_key: str,
    preferred_template_key: str | None = None,
    channel: str | None = None,
    recipient_strategy: str = "origin_primary",
    recipient_config: Mapping[str, Any] | None = None,
    conditions: Mapping[str, Any] | None = None,
    variables_mapping: Mapping[str, Any] | None = None,
    triggers: Sequence[tuple[str, Mapping[str, Any]]] | Sequence[TriggerSpec] = (),
    meta: Mapping[str, Any] | None = None,
) -> RuleVersionPayload:
    trigger_specs: list[TriggerSpec] = []
    for item in triggers:
        if isinstance(item, TriggerSpec):
            trigger_specs.append(item)
        else:
            event_type, event_filter = item
            trigger_specs.append(
                TriggerSpec(
                    event_type=str(event_type),
                    event_filter=dict(event_filter or {}),
                )
            )
    return RuleVersionPayload(
        rule_id=str(rule_id),
        rule_version_id=str(rule_version_id),
        version_status=str(version_status),
        rule_status=str(rule_status),
        enabled=bool(enabled),
        intent_key=str(intent_key or ""),
        preferred_template_key=preferred_template_key,
        channel=channel,
        recipient_strategy=str(recipient_strategy or "origin_primary"),
        recipient_config=dict(recipient_config or {}),
        conditions=dict(conditions or {}),
        variables_mapping=dict(variables_mapping or {}),
        triggers=tuple(trigger_specs),
        meta=dict(meta or {}),
    )


def rule_version_to_payload(
    version: CommunicationAutomationRuleVersion,
    *,
    rule: CommunicationAutomationRule,
) -> RuleVersionPayload:
    triggers = [
        TriggerSpec(
            event_type=str(t.event_type),
            event_filter=dict(t.event_filter or {}),
        )
        for t in (version.triggers or [])
    ]
    return build_rule_payload(
        rule_id=str(rule.id),
        rule_version_id=str(version.id),
        version_status=str(version.status),
        rule_status=str(rule.status),
        enabled=bool(rule.enabled),
        intent_key=str(version.intent_key or ""),
        preferred_template_key=version.preferred_template_key,
        channel=version.channel,
        recipient_strategy=str(version.recipient_strategy or "origin_primary"),
        recipient_config=dict(version.recipient_config or {}),
        conditions=dict(version.conditions or {}),
        variables_mapping=dict(version.variables_mapping or {}),
        triggers=triggers,
        meta=dict(version.meta or {}),
    )


__all__ = ["build_rule_payload", "rule_version_to_payload"]
