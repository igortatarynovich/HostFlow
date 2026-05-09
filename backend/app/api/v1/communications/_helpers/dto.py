"""DTO converters: ORM rows → Pydantic ``*Out`` models for the communications API.

Pure data-transformation functions with no DB / network side effects.
Extracted in Phase 1 god-module split, step 3/N. Re-exported from
``backend.app.api.v1.communications`` for backward compatibility.
"""

from __future__ import annotations

from backend.app.models.communication import (
    CommunicationAllocationAudit,
    CommunicationCommandAudit,
    CommunicationMessage,
    CommunicationThread,
    CommunicationTimeOffRequest,
)

from ..schemas import (
    CommunicationAllocationAuditOut,
    CommunicationCommandAuditOut,
    CommunicationMessageOut,
    CommunicationThreadOut,
    TimeOffRequestOut,
)
from .utils import _as_dict, _as_list

__all__ = [
    "_thread_out",
    "_message_out",
    "_timeoff_out",
    "_allocation_audit_out",
    "_command_audit_out",
]


def _thread_out(thread: CommunicationThread) -> CommunicationThreadOut:
    return CommunicationThreadOut(
        id=str(thread.id),
        channel=thread.channel,
        channel_account_id=thread.channel_account_id,
        channel_thread_ref=thread.channel_thread_ref,
        subject=thread.subject,
        status=thread.status,
        direction_hint=thread.direction_hint,
        entity_type=thread.entity_type,
        entity_id=thread.entity_id,
        linked_company_id=thread.linked_company_id,
        linked_candidate_id=thread.linked_candidate_id,
        owner_id=thread.owner_id,
        assignee_id=thread.assignee_id,
        queue_assigned_by=thread.queue_assigned_by,
        priority=thread.priority,
        sla_due_at=thread.sla_due_at,
        participants_json=_as_dict(thread.participants_json),
        tags_json=_as_list(thread.tags_json),
        thread_meta=_as_dict(thread.thread_meta),
        last_message_at=thread.last_message_at,
        last_inbound_at=thread.last_inbound_at,
        last_outbound_at=thread.last_outbound_at,
        last_message_preview=thread.last_message_preview,
        unread_count=int(thread.unread_count or 0),
        is_archived=bool(thread.is_archived),
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


def _message_out(msg: CommunicationMessage) -> CommunicationMessageOut:
    return CommunicationMessageOut(
        id=str(msg.id),
        thread_id=str(msg.thread_id),
        channel=msg.channel,
        message_type=msg.message_type,
        direction=msg.direction,
        sender_type=msg.sender_type,
        sender_id=msg.sender_id,
        sender_label=msg.sender_label,
        sender_address=msg.sender_address,
        recipient_type=msg.recipient_type,
        recipient_id=msg.recipient_id,
        recipient_label=msg.recipient_label,
        recipient_address=msg.recipient_address,
        subject=msg.subject,
        body_text=msg.body_text,
        body_html=msg.body_html,
        attachments_json=_as_list(msg.attachments_json),
        payload=_as_dict(msg.payload),
        external_message_ref=msg.external_message_ref,
        delivery_status=msg.delivery_status,
        error_message=msg.error_message,
        sent_at=msg.sent_at,
        delivered_at=msg.delivered_at,
        read_at=msg.read_at,
        is_internal_note=bool(msg.is_internal_note),
        created_at=msg.created_at,
        updated_at=msg.updated_at,
    )


def _timeoff_out(row: CommunicationTimeOffRequest) -> TimeOffRequestOut:
    return TimeOffRequestOut(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        requester_user_id=str(row.requester_user_id),
        requester_label=row.requester_label,
        approver_user_id=row.approver_user_id,
        approver_label=row.approver_label,
        request_type=row.request_type,
        status=row.status,
        start_date=row.start_date,
        end_date=row.end_date,
        partial_day=row.partial_day,
        reason=row.reason,
        decision_note=row.decision_note,
        requested_at=row.requested_at,
        decided_at=row.decided_at,
        payload=_as_dict(row.payload),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# Phase 2.1 (ADR-012, 2026-05-09): ``_planner_event_out`` removed
# along with the legacy planner-event HTTP routes. Activity rows are
# serialised by ``ReminderOut.from_model`` /
# ``ActivityOut.from_model`` in ``backend/app/api/v1/reminders_v2.py``
# / ``activities_v1.py`` instead.


def _allocation_audit_out(row: CommunicationAllocationAudit) -> CommunicationAllocationAuditOut:
    candidates = row.candidates_json if isinstance(row.candidates_json, list) else []
    normalized_candidates = [c for c in candidates if isinstance(c, dict)]
    return CommunicationAllocationAuditOut(
        id=str(row.id),
        mode=row.mode,
        channel=row.channel,
        thread_id=row.thread_id,
        actor_user_id=row.actor_user_id,
        strategy=row.strategy,
        assigned=bool(row.assigned),
        assignee_id=row.assignee_id,
        reason=row.reason,
        evaluated_at=row.evaluated_at,
        candidates_json=normalized_candidates,
        payload=_as_dict(row.payload),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _command_audit_out(row: CommunicationCommandAudit) -> CommunicationCommandAuditOut:
    actions = row.actions_json if isinstance(row.actions_json, list) else []
    normalized_actions = [a for a in actions if isinstance(a, dict)]
    return CommunicationCommandAuditOut(
        id=str(row.id),
        thread_id=str(row.thread_id),
        channel=row.channel,
        command_id=row.command_id,
        command_label=row.command_label,
        actor_user_id=row.actor_user_id,
        action_count=int(row.action_count or 0),
        actions_json=normalized_actions,
        payload=_as_dict(row.payload),
        executed_at=row.executed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
