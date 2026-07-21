"""ORM → pure audience payload adapters (C2.3 PR-2).

Not part of the pure resolver package — may import models.
"""

from __future__ import annotations

from backend.app.communications.campaign.audience.types import AudienceDefinitionPayload
from backend.app.models.communication_campaign import (
    CommunicationCampaignAudienceDefinition,
    CommunicationCampaignVersion,
)


def audience_definition_to_payload(
    row: CommunicationCampaignAudienceDefinition,
    *,
    version_id: str | None = None,
) -> AudienceDefinitionPayload:
    return AudienceDefinitionPayload(
        definition_type=str(row.definition_type or "").strip().lower(),
        definition=dict(row.definition or {}),
        meta=dict(row.meta or {}),
        version_id=version_id or str(row.version_id),
    )


def version_audience_payload(
    version: CommunicationCampaignVersion,
) -> AudienceDefinitionPayload | None:
    row = version.audience_definition
    if row is None:
        return None
    return audience_definition_to_payload(row, version_id=str(version.id))


__all__ = [
    "audience_definition_to_payload",
    "version_audience_payload",
]
