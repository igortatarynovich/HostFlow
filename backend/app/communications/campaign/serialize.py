"""Serialize Campaign domain rows for HTTP API (C2.3 PR-5)."""

from __future__ import annotations

from typing import Any

from backend.app.models.communication_campaign import (
    CommunicationCampaign,
    CommunicationCampaignAudienceDefinition,
    CommunicationCampaignRecipient,
    CommunicationCampaignRun,
    CommunicationCampaignRunItem,
    CommunicationCampaignVersion,
)


def serialize_audience_definition(
    row: CommunicationCampaignAudienceDefinition | None,
) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": str(row.id),
        "definition_type": row.definition_type,
        "definition": dict(row.definition or {}),
        "meta": dict(row.meta or {}),
    }


def serialize_version(
    version: CommunicationCampaignVersion,
    *,
    include_body: bool = True,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(version.id),
        "campaign_id": str(version.campaign_id),
        "version_number": int(version.version_number or 0),
        "status": version.status,
        "intent_key": version.intent_key,
        "preferred_template_key": version.preferred_template_key,
        "channel": version.channel,
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "published_by": version.published_by,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "updated_at": version.updated_at.isoformat() if version.updated_at else None,
    }
    if include_body:
        data["plan"] = dict(version.plan or {})
        data["meta"] = dict(version.meta or {})
        data["audience_definition"] = serialize_audience_definition(
            version.audience_definition
        )
    return data


def serialize_campaign(
    campaign: CommunicationCampaign,
    *,
    draft: CommunicationCampaignVersion | None = None,
    latest_published: CommunicationCampaignVersion | None = None,
) -> dict[str, Any]:
    return {
        "id": str(campaign.id),
        "key": campaign.key,
        "name": campaign.name,
        "description": campaign.description,
        "status": campaign.status,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
        "draft": serialize_version(draft) if draft is not None else None,
        "latest_published": (
            serialize_version(latest_published) if latest_published is not None else None
        ),
    }


def serialize_recipient(row: CommunicationCampaignRecipient) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "address": row.address,
        "label": row.label,
        "snapshot": dict(row.snapshot or {}),
    }


def serialize_run_item(row: CommunicationCampaignRunItem) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "recipient_id": str(row.recipient_id),
        "status": row.status,
        "reason_codes": list(row.reason_codes or []),
        "reason_message": row.reason_message,
        "intent_key": row.intent_key,
        "source_event_id": row.source_event_id,
        "meta": dict(row.meta or {}),
    }


def serialize_run(
    run: CommunicationCampaignRun,
    *,
    include_items: bool = True,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(run.id),
        "campaign_id": str(run.campaign_id),
        "campaign_version_id": str(run.campaign_version_id),
        "idempotency_key": run.idempotency_key,
        "status": run.status,
        "audience_snapshot": dict(run.audience_snapshot or {}),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "meta": dict(run.meta or {}),
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        "recipient_count": len(run.recipients or []),
    }
    if include_items:
        data["recipients"] = [serialize_recipient(r) for r in (run.recipients or [])]
        data["items"] = [serialize_run_item(i) for i in (run.items or [])]
    return data


__all__ = [
    "serialize_audience_definition",
    "serialize_version",
    "serialize_campaign",
    "serialize_recipient",
    "serialize_run_item",
    "serialize_run",
]
