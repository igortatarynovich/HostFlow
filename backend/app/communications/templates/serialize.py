"""Serialize Template domain rows for HTTP API (PR-4)."""

from __future__ import annotations

from typing import Any

from backend.app.models.communication_template import (
    CommunicationTemplate,
    CommunicationTemplateVersion,
)


def serialize_variable(v: Any) -> dict[str, Any]:
    return {
        "id": str(v.id),
        "name": v.name,
        "var_type": v.var_type,
        "required": bool(v.required),
        "description": v.description,
        "default_value": v.default_value,
    }


def serialize_version(
    version: CommunicationTemplateVersion,
    *,
    include_body: bool = True,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(version.id),
        "template_id": str(version.template_id),
        "version_number": int(version.version_number or 0),
        "status": version.status,
        "locale": version.locale,
        "channels": sorted(
            str(c.channel) for c in (version.channel_bindings or []) if c.channel
        ),
        "intent_keys": sorted(
            str(i.intent_key) for i in (version.intent_bindings or []) if i.intent_key
        ),
        "variables": [serialize_variable(v) for v in (version.variables or [])],
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "published_by": version.published_by,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "updated_at": version.updated_at.isoformat() if version.updated_at else None,
    }
    if include_body:
        data["subject"] = version.subject
        data["body_text"] = version.body_text
        data["body_html"] = version.body_html
        data["meta"] = dict(version.meta or {})
    return data


def serialize_template(
    template: CommunicationTemplate,
    *,
    draft: CommunicationTemplateVersion | None = None,
    latest_published: CommunicationTemplateVersion | None = None,
) -> dict[str, Any]:
    return {
        "id": str(template.id),
        "key": template.key,
        "name": template.name,
        "description": template.description,
        "status": template.status,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        "draft": serialize_version(draft) if draft is not None else None,
        "latest_published": (
            serialize_version(latest_published) if latest_published is not None else None
        ),
    }


__all__ = ["serialize_variable", "serialize_version", "serialize_template"]
