from __future__ import annotations

from backend.app.services.user_notifications import (
    notification_out_priority,
    resolve_notification_priority,
)
from backend.app.models.user_notification import UserNotification


def test_resolve_sla_events_critical() -> None:
    assert resolve_notification_priority("communications_sla_overdue", {}) == "critical"
    assert resolve_notification_priority("communications_thread_escalated", {}) == "critical"
    assert resolve_notification_priority("lead_rodo_delivery_escalated", {}) == "critical"


def test_resolve_lead_nudges_are_normal_not_sla_critical() -> None:
    assert (
        resolve_notification_priority(
            "lead_no_next_action",
            {"source": "leads_next_action_sla"},
        )
        == "normal"
    )
    assert (
        resolve_notification_priority(
            "lead_stuck_stage",
            {"source": "leads_next_action_sla"},
        )
        == "normal"
    )


def test_resolve_handoff_high() -> None:
    assert resolve_notification_priority("handoff_requested", {}) == "high"
    assert resolve_notification_priority("reminder_overdue", {}) == "high"


def test_payload_priority_override() -> None:
    assert (
        resolve_notification_priority(
            "some_noise",
            {"priority": "normal", "source": "leads_next_action_sla"},
        )
        == "normal"
    )


def test_notification_out_priority_uses_column() -> None:
    row = UserNotification(
        id="x",
        tenant_id="t",
        user_id="u",
        event_type="handoff_requested",
        priority="normal",
        entity_type=None,
        entity_id=None,
        payload={},
        channel="in_app",
        is_read=False,
    )
    assert notification_out_priority(row) == "normal"
