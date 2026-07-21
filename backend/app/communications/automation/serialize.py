"""Serialize Automation domain rows for HTTP API (C2.2 PR-4)."""

from __future__ import annotations

from typing import Any

from backend.app.models.communication_automation import (
    CommunicationAutomationDecision,
    CommunicationAutomationRule,
    CommunicationAutomationRuleVersion,
    CommunicationAutomationTrigger,
)


def serialize_trigger(t: CommunicationAutomationTrigger) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "event_type": t.event_type,
        "event_filter": dict(t.event_filter or {}),
    }


def serialize_version(
    version: CommunicationAutomationRuleVersion,
    *,
    include_body: bool = True,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(version.id),
        "rule_id": str(version.rule_id),
        "version_number": int(version.version_number or 0),
        "status": version.status,
        "intent_key": version.intent_key,
        "preferred_template_key": version.preferred_template_key,
        "channel": version.channel,
        "recipient_strategy": version.recipient_strategy,
        "triggers": [serialize_trigger(t) for t in (version.triggers or [])],
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "published_by": version.published_by,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "updated_at": version.updated_at.isoformat() if version.updated_at else None,
    }
    if include_body:
        data["conditions"] = dict(version.conditions or {})
        data["recipient_config"] = dict(version.recipient_config or {})
        data["variables_mapping"] = dict(version.variables_mapping or {})
        data["meta"] = dict(version.meta or {})
    return data


def serialize_rule(
    rule: CommunicationAutomationRule,
    *,
    draft: CommunicationAutomationRuleVersion | None = None,
    latest_published: CommunicationAutomationRuleVersion | None = None,
) -> dict[str, Any]:
    return {
        "id": str(rule.id),
        "key": rule.key,
        "name": rule.name,
        "description": rule.description,
        "status": rule.status,
        "enabled": bool(rule.enabled),
        "priority": int(rule.priority or 0),
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        "draft": serialize_version(draft) if draft is not None else None,
        "latest_published": (
            serialize_version(latest_published) if latest_published is not None else None
        ),
    }


def serialize_decision(d: CommunicationAutomationDecision) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "rule_id": str(d.rule_id),
        "rule_version_id": str(d.rule_version_id),
        "trigger_id": d.trigger_id,
        "source_event_id": d.source_event_id,
        "event_type": d.event_type,
        "outcome": d.outcome,
        "reason_codes": list(d.reason_codes or []),
        "intent_key": d.intent_key,
        "intent_request_snapshot": (
            dict(d.intent_request_snapshot) if d.intent_request_snapshot else None
        ),
        "correlation_id": d.correlation_id,
        "meta": dict(d.meta or {}),
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


__all__ = [
    "serialize_trigger",
    "serialize_version",
    "serialize_rule",
    "serialize_decision",
]
