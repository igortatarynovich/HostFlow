from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.services.notification_templates import (
    iter_channel_templates,
    list_notification_templates,
)


def seed_notification_templates(
    conn: Connection, *, tenant_id: str, user_id: str
) -> None:
    """
    Populate dev/demo notification entries aligned with template metadata.
    Existing seed notifications (payload.seed == true) are removed to keep the
    dataset idempotent.
    """

    conn.execute(
        text(
            "DELETE FROM user_notifications "
            "WHERE json_extract(payload, '$.seed') = 1"
        )
    )

    templates = list_notification_templates()
    now = datetime.now(timezone.utc).isoformat()

    for template in templates:
        channel_templates: Dict[str, Dict[str, Any]] = {}
        localization_keys = set()
        for channel_def in iter_channel_templates(template):
            channel_templates[channel_def.channel] = {
                "template_key": channel_def.template_key,
                "subject_key": channel_def.subject_key,
                "body_key": channel_def.body_key,
                "default_subject": channel_def.default_subject,
                "default_body": channel_def.default_body,
            }
            for lk in (
                channel_def.template_key,
                channel_def.subject_key,
                channel_def.body_key,
            ):
                if lk:
                    localization_keys.add(lk)

        payload = {
            "seed": True,
            "template_slug": template.slug,
            "event_type": template.event_type,
            "metadata": template.metadata,
            "variables": template.variables,
            "channel_templates": channel_templates,
            "localization_keys": sorted(localization_keys),
        }

        conn.execute(
            text(
                """
                INSERT INTO user_notifications (
                    id,
                    tenant_id,
                    user_id,
                    event_type,
                    entity_type,
                    entity_id,
                    payload,
                    channel,
                    is_read,
                    delivered_at,
                    created_at,
                    updated_at
                )
                VALUES (
                    :id,
                    :tenant_id,
                    :user_id,
                    :event_type,
                    :entity_type,
                    :entity_id,
                    :payload,
                    :channel,
                    :is_read,
                    :delivered_at,
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "user_id": user_id,
                "event_type": template.event_type,
                "entity_type": "document",
                "entity_id": f"seed::{template.slug}",
                "payload": json.dumps(payload),
                "channel": "in_app",
                "is_read": 0,
                "delivered_at": now,
                "created_at": now,
                "updated_at": now,
            },
        )

