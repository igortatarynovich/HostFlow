"""Pydantic request/response schemas for the communications API.

Extracted from the legacy monolithic ``backend/app/api/v1/communications.py``
as part of Phase 1 god-module decomposition (see
``docs/HOSTFLOW_AUDIT_AND_PLAN.md``).

All public names are re-exported via ``backend.app.api.v1.communications``
(``__init__.py``) to preserve the existing import surface for callers such as
``backend/app/services/communications_scheduler.py`` and tests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field

__all__ = [
    "MAX_COMM_MESSAGE_ATTACHMENT_BYTES",
    "WorkingHoursWindowIn",
    "WorkingHoursDayIn",
    "WorkingHoursScheduleIn",
    "WorkingHoursScheduleOut",
    "NotificationSettingsIn",
    "NotificationSettingsOut",
    "CommunicationThreadOut",
    "CommunicationThreadResultLinkOut",
    "CommunicationThreadResultLinkAttach",
    "CommunicationMessageOut",
    "CommunicationThreadListResponse",
    "CommunicationMessageListResponse",
    "CommunicationMessageTemplateOut",
    "CommunicationMessageTemplateListResponse",
    "CommunicationThreadDetailResponse",
    "CommunicationThreadCreate",
    "CommunicationThreadPatch",
    "CommunicationMessageAttachmentUploadOut",
    "CommunicationMessageCreate",
    "CommunicationMarkReadRequest",
    "CommunicationUnreadReconcileRequest",
    "CommunicationUnreadReconcileResponse",
    "CommunicationAutoAssignResponse",
    "CommunicationAllocatorPreviewRequest",
    "CommunicationAllocatorPreviewResponse",
    "CommunicationAllocationAuditOut",
    "CommunicationAllocationAuditListResponse",
    "CommunicationCommandAuditOut",
    "CommunicationCommandAuditListResponse",
    "CommunicationCommandAuditBatchCreate",
    "CommunicationCommandAuditBatchResponse",
    "CommunicationChannelAccountOut",
    "CommunicationChannelAccountListResponse",
    "CommunicationChannelAccountCreate",
    "CommunicationChannelAccountPatch",
    "EmailIngestRequest",
    "EmailIngestResponse",
    "GenericInboundIngestRequest",
    "GenericInboundIngestResponse",
    "CommunicationDispatchRequest",
    "CommunicationDispatchResponse",
    "CommunicationDispatchQueuedRequest",
    "CommunicationDispatchQueuedResponse",
    "CommunicationDeliveryStatusPatch",
    "CommunicationAccountActionResponse",
    "CommunicationAccountOAuthStartRequest",
    "CommunicationAccountOAuthStartResponse",
    "CommunicationAccountOAuthCompleteRequest",
    "CommunicationAccountOAuthCompleteResponse",
    "CommunicationAccountOAuthRefreshRequest",
    "CommunicationAccountSyncCursorPatch",
    "CommunicationAccountSyncCursorOut",
    "TelegramWebhookSimulateRequest",
    "CommunicationEmailWorkerDispatchRequest",
    "CommunicationEmailWorkerPollRequest",
    "CommunicationEmailWorkerPollResponse",
    "CommunicationSchedulerStatusOut",
    "CommunicationSchedulerRunNowResponse",
    # Phase 2.1 (ADR-012, 2026-05-09): CommunicationPlannerEvent* schemas
    # removed together with the legacy planner-event HTTP routes. The
    # canonical task / planner-row schemas live in
    # ``backend/app/api/v1/reminders_v2.py`` and ``activities_v1.py``.
    "TimeOffRequestOut",
    "TimeOffRequestListResponse",
    "TimeOffRequestCreate",
    "TimeOffRequestDecision",
    "TimeOffRequestCancel",
]


# 25 MiB hard cap for individual outbound communication-message attachments.
# Kept module-scoped because routes and helpers across the package check it
# directly (``from .schemas import MAX_COMM_MESSAGE_ATTACHMENT_BYTES``).
MAX_COMM_MESSAGE_ATTACHMENT_BYTES = 25 * 1024 * 1024


# ---------------------------------------------------------------------------
# Working-hours helpers (used by /accounts and tenant-settings endpoints).
# ---------------------------------------------------------------------------


class WorkingHoursWindowIn(BaseModel):
    from_: str = Field(alias="from")
    to: str


class WorkingHoursDayIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    enabled: bool = True
    windows: List[WorkingHoursWindowIn] = Field(default_factory=list)


class WorkingHoursScheduleIn(BaseModel):
    tz: str | None = None
    days: List[WorkingHoursDayIn] = Field(default_factory=list)


class WorkingHoursScheduleOut(BaseModel):
    tz: str | None = None
    days: List[Dict[str, Any]] = Field(default_factory=list)


class NotificationSettingsIn(BaseModel):
    default_reminder_minutes: int = Field(default=30, ge=0, le=1440)
    channels: Dict[str, bool] = Field(default_factory=lambda: {"in_app": True, "push": True, "email": False})
    quiet_hours_enabled: bool = False
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str | None = None


class NotificationSettingsOut(BaseModel):
    default_reminder_minutes: int = Field(default=30, ge=0, le=1440)
    channels: Dict[str, bool] = Field(default_factory=dict)
    quiet_hours_enabled: bool = False
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str | None = None


# ---------------------------------------------------------------------------
# Threads, messages, templates.
# ---------------------------------------------------------------------------


class CommunicationThreadResultLinkOut(BaseModel):
    """C1 opaque Thread → destination result pointer (no domain ORM)."""

    link_id: str
    thread_id: str
    module_owner: str
    result_type: str
    result_id: str
    ledger_id: str | None = None
    status: str
    provenance_ref: str | None = None


class CommunicationThreadOut(BaseModel):
    id: str
    channel: str
    channel_account_id: str | None = None
    channel_thread_ref: str | None = None
    subject: str | None = None
    status: str
    direction_hint: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    linked_company_id: str | None = None
    linked_candidate_id: str | None = None
    owner_id: str | None = None
    assignee_id: str | None = None
    queue_assigned_by: str | None = None
    priority: str
    sla_due_at: datetime | None = None
    participants_json: Dict[str, Any] = Field(default_factory=dict)
    tags_json: List[Any] = Field(default_factory=list)
    thread_meta: Dict[str, Any] = Field(default_factory=dict)
    last_message_at: datetime | None = None
    last_inbound_at: datetime | None = None
    last_outbound_at: datetime | None = None
    last_message_preview: str | None = None
    unread_count: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    result_link: CommunicationThreadResultLinkOut | None = None


class CommunicationMessageOut(BaseModel):
    id: str
    thread_id: str
    channel: str
    message_type: str
    direction: str
    sender_type: str | None = None
    sender_id: str | None = None
    sender_label: str | None = None
    sender_address: str | None = None
    recipient_type: str | None = None
    recipient_id: str | None = None
    recipient_label: str | None = None
    recipient_address: str | None = None
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    attachments_json: List[Any] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    external_message_ref: str | None = None
    delivery_status: str
    error_message: str | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    is_internal_note: bool
    created_at: datetime
    updated_at: datetime


class CommunicationThreadListResponse(BaseModel):
    items: List[CommunicationThreadOut]
    total: int


class CommunicationMessageListResponse(BaseModel):
    items: List[CommunicationMessageOut]
    total: int


class CommunicationMessageTemplateOut(BaseModel):
    id: str
    label: str
    body: str
    visibility: str = "private"
    target: str = "messages"
    owner_user_id: str | None = None
    enabled: bool = True


class CommunicationMessageTemplateListResponse(BaseModel):
    items: List[CommunicationMessageTemplateOut] = Field(default_factory=list)
    total: int = 0


class CommunicationThreadDetailResponse(BaseModel):
    thread: CommunicationThreadOut
    messages: List[CommunicationMessageOut] = Field(default_factory=list)


class CommunicationThreadCreate(BaseModel):
    channel: str = Field(..., min_length=2, max_length=32)
    subject: str | None = Field(default=None, max_length=512)
    status: str = Field(default="open", max_length=32)
    direction_hint: str | None = Field(default=None, max_length=16)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=120)
    linked_company_id: str | None = Field(default=None, max_length=36)
    linked_candidate_id: str | None = Field(default=None, max_length=36)
    assignee_id: str | None = Field(default=None, max_length=36)
    priority: str = Field(default="normal", max_length=16)
    participants_json: Dict[str, Any] = Field(default_factory=dict)
    tags_json: List[Any] = Field(default_factory=list)
    thread_meta: Dict[str, Any] = Field(default_factory=dict)
    channel_account_id: str | None = Field(default=None, max_length=36)
    channel_thread_ref: str | None = Field(default=None, max_length=255)
    auto_assign: bool = False
    # C1 — opaque result link (SoT). Do not infer from entity_type / Lead / form.
    result_module_owner: str | None = Field(default=None, max_length=32)
    result_type: str | None = Field(default=None, max_length=64)
    result_id: str | None = Field(default=None, max_length=64)
    provenance_ledger_id: str | None = Field(default=None, max_length=36)


class CommunicationThreadResultLinkAttach(BaseModel):
    """Attach opaque result (or copy from confirmed Flights ledger)."""

    module_owner: str | None = Field(default=None, max_length=32)
    result_type: str | None = Field(default=None, max_length=64)
    result_id: str | None = Field(default=None, max_length=64)
    provenance_ledger_id: str | None = Field(default=None, max_length=36)


class CommunicationThreadPatch(BaseModel):
    subject: str | None = Field(default=None, max_length=512)
    status: str | None = Field(default=None, max_length=32)
    assignee_id: str | None = Field(default=None, max_length=36)
    linked_company_id: str | None = Field(default=None, max_length=36)
    linked_candidate_id: str | None = Field(default=None, max_length=36)
    queue_assigned_by: str | None = Field(default=None, max_length=32)
    priority: str | None = Field(default=None, max_length=16)
    is_archived: bool | None = None
    unread_count: int | None = Field(default=None, ge=0)
    participants_json: Dict[str, Any] | None = None
    tags_json: List[Any] | None = None
    thread_meta: Dict[str, Any] | None = None


class CommunicationMessageAttachmentUploadOut(BaseModel):
    kind: str = "local_file"
    filename: str
    mime: str | None = None
    size: int
    storage_path: str


class CommunicationMessageCreate(BaseModel):
    message_type: str = Field(default="text", max_length=32)
    direction: str = Field(..., pattern="^(inbound|outbound|system)$")
    sender_type: str | None = Field(default=None, max_length=32)
    sender_id: str | None = Field(default=None, max_length=36)
    sender_label: str | None = Field(default=None, max_length=255)
    sender_address: str | None = Field(default=None, max_length=255)
    recipient_type: str | None = Field(default=None, max_length=32)
    recipient_id: str | None = Field(default=None, max_length=36)
    recipient_label: str | None = Field(default=None, max_length=255)
    recipient_address: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=512)
    body_text: str | None = None
    body_html: str | None = None
    attachments_json: List[Any] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    external_message_ref: str | None = Field(default=None, max_length=255)
    delivery_status: str = Field(default="queued", max_length=32)
    is_internal_note: bool = False
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None


class CommunicationMarkReadRequest(BaseModel):
    message_ids: List[str] | None = None
    mark_thread: bool = True


class CommunicationUnreadReconcileRequest(BaseModel):
    channel: str | None = Field(default=None, max_length=32)
    include_archived: bool = False
    limit: int = Field(default=1000, ge=1, le=5000)


class CommunicationUnreadReconcileResponse(BaseModel):
    processed: int
    updated: int
    total_unread: int


class CommunicationAutoAssignResponse(BaseModel):
    assigned: bool
    thread: CommunicationThreadOut
    reason: str | None = None
    strategy: str | None = None
    assignee_id: str | None = None
    candidates: List[Dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Allocator + commands audit.
# ---------------------------------------------------------------------------


class CommunicationAllocatorPreviewRequest(BaseModel):
    channel: str = Field(..., min_length=2, max_length=32)
    at: datetime | None = None
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=120)


class CommunicationAllocatorPreviewResponse(BaseModel):
    assigned: bool
    reason: str | None = None
    strategy: str | None = None
    assignee_id: str | None = None
    evaluated_at: str | None = None
    candidates: List[Dict[str, Any]] = Field(default_factory=list)


class CommunicationAllocationAuditOut(BaseModel):
    id: str
    mode: str
    channel: str
    thread_id: str | None = None
    actor_user_id: str | None = None
    strategy: str | None = None
    assigned: bool
    assignee_id: str | None = None
    reason: str | None = None
    evaluated_at: datetime | None = None
    candidates_json: List[Dict[str, Any]] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CommunicationAllocationAuditListResponse(BaseModel):
    items: List[CommunicationAllocationAuditOut]
    total: int


class CommunicationCommandAuditOut(BaseModel):
    id: str
    thread_id: str
    channel: str
    command_id: str
    command_label: str | None = None
    actor_user_id: str | None = None
    action_count: int
    actions_json: List[Dict[str, Any]] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CommunicationCommandAuditListResponse(BaseModel):
    items: List[CommunicationCommandAuditOut]
    total: int


class CommunicationCommandAuditBatchCreate(BaseModel):
    channel: str = Field(..., min_length=2, max_length=32)
    thread_ids: List[str] = Field(default_factory=list)
    command_id: str = Field(..., min_length=1, max_length=64)
    command_label: str | None = Field(default=None, max_length=255)
    actions_json: List[Dict[str, Any]] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime | None = None


class CommunicationCommandAuditBatchResponse(BaseModel):
    created: int
    items: List[CommunicationCommandAuditOut]


# ---------------------------------------------------------------------------
# Channel accounts + ingestion + dispatch + delivery.
# ---------------------------------------------------------------------------


class CommunicationChannelAccountOut(BaseModel):
    id: str
    channel: str
    account_label: str
    external_account_ref: str | None = None
    inbox_address: str | None = None
    is_active: bool
    settings_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CommunicationChannelAccountListResponse(BaseModel):
    items: List[CommunicationChannelAccountOut]


class CommunicationChannelAccountCreate(BaseModel):
    channel: str = Field(..., min_length=2, max_length=32)
    account_label: str = Field(..., min_length=1, max_length=255)
    external_account_ref: str | None = Field(default=None, max_length=255)
    inbox_address: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    settings_json: Dict[str, Any] = Field(default_factory=dict)
    # Top-level secret avoids some clients/proxies mishandling nested oauth.client_secret JSON.
    oauth_client_secret: str | None = Field(default=None, max_length=2048)


class CommunicationChannelAccountPatch(BaseModel):
    account_label: str | None = Field(default=None, min_length=1, max_length=255)
    external_account_ref: str | None = Field(default=None, max_length=255)
    inbox_address: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    settings_json: Dict[str, Any] | None = None
    oauth_client_secret: str | None = Field(default=None, max_length=2048)


class EmailIngestRequest(BaseModel):
    channel_account_id: str | None = Field(default=None, max_length=36)
    provider: str | None = Field(default=None, max_length=64)
    provider_thread_ref: str | None = Field(default=None, max_length=255)
    external_message_ref: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=512)
    from_address: str | None = Field(default=None, max_length=255)
    from_name: str | None = Field(default=None, max_length=255)
    to_address: str | None = Field(default=None, max_length=255)
    to_name: str | None = Field(default=None, max_length=255)
    cc: List[str] = Field(default_factory=list)
    bcc: List[str] = Field(default_factory=list)
    text: str | None = None
    html: str | None = None
    received_at: datetime | None = None
    headers: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=120)
    linked_candidate_id: str | None = Field(default=None, max_length=36)
    linked_company_id: str | None = Field(default=None, max_length=36)
    assignee_id: str | None = Field(default=None, max_length=36)
    auto_assign: bool = True


class EmailIngestResponse(BaseModel):
    created_thread: bool
    duplicate_message: bool
    auto_assigned: bool = False
    auto_assign_reason: str | None = None
    thread: CommunicationThreadOut
    message: CommunicationMessageOut


class GenericInboundIngestRequest(BaseModel):
    channel_account_id: str | None = Field(default=None, max_length=36)
    provider: str | None = Field(default=None, max_length=64)
    provider_thread_ref: str | None = Field(default=None, max_length=255)
    provider_chat_ref: str | None = Field(default=None, max_length=255)
    external_message_ref: str | None = Field(default=None, max_length=255)
    sender_address: str | None = Field(default=None, max_length=255)
    sender_label: str | None = Field(default=None, max_length=255)
    recipient_address: str | None = Field(default=None, max_length=255)
    recipient_label: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=512)
    text: str | None = None
    html: str | None = None
    received_at: datetime | None = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, Any] = Field(default_factory=dict)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=120)
    linked_candidate_id: str | None = Field(default=None, max_length=36)
    linked_company_id: str | None = Field(default=None, max_length=36)
    assignee_id: str | None = Field(default=None, max_length=36)
    auto_assign: bool = True


class GenericInboundIngestResponse(BaseModel):
    created_thread: bool
    duplicate_message: bool
    auto_assigned: bool = False
    auto_assign_reason: str | None = None
    thread: CommunicationThreadOut
    message: CommunicationMessageOut


class CommunicationDispatchRequest(BaseModel):
    mark_delivered: bool = True
    simulate_failure: bool = False
    provider_message_ref: str | None = Field(default=None, max_length=255)
    provider_payload: Dict[str, Any] = Field(default_factory=dict)


class CommunicationDispatchResponse(BaseModel):
    dispatched: bool
    message: CommunicationMessageOut
    thread: CommunicationThreadOut
    reason: str | None = None


class CommunicationDispatchQueuedRequest(BaseModel):
    limit: int = Field(default=25, ge=1, le=200)
    channel: str | None = Field(default=None, max_length=32)
    only_email: bool = False
    mark_delivered: bool = True
    simulate_failure: bool = False


class CommunicationDispatchQueuedResponse(BaseModel):
    processed: int
    dispatched: int
    failed: int
    items: List[CommunicationDispatchResponse] = Field(default_factory=list)


class CommunicationDeliveryStatusPatch(BaseModel):
    delivery_status: str = Field(..., max_length=32)
    error_message: str | None = None
    external_message_ref: str | None = Field(default=None, max_length=255)
    provider_payload: Dict[str, Any] = Field(default_factory=dict)
    delivered_at: datetime | None = None
    read_at: datetime | None = None


# ---------------------------------------------------------------------------
# Account actions: connection, OAuth, sync cursors, telegram simulate.
# ---------------------------------------------------------------------------


class CommunicationAccountActionResponse(BaseModel):
    ok: bool
    action: str
    status: str
    account: CommunicationChannelAccountOut
    detail: str | None = None


class CommunicationAccountOAuthStartRequest(BaseModel):
    redirect_uri: str | None = Field(default=None, max_length=2048)
    client_id: str | None = Field(default=None, max_length=512)
    scopes: List[str] = Field(default_factory=list)
    force_consent: bool = False


class CommunicationAccountOAuthStartResponse(BaseModel):
    ok: bool
    action: str
    provider: str
    state: str
    auth_url: str
    account: CommunicationChannelAccountOut


class CommunicationAccountOAuthCompleteRequest(BaseModel):
    state: str = Field(..., min_length=8, max_length=256)
    code: str | None = Field(default=None, max_length=4096)
    redirect_uri: str | None = Field(default=None, max_length=2048)
    client_id: str | None = Field(default=None, max_length=512)
    access_token: str | None = Field(default=None, max_length=8192)
    refresh_token: str | None = Field(default=None, max_length=8192)
    token_type: str | None = Field(default="Bearer", max_length=64)
    expires_in: int | None = Field(default=3600, ge=60, le=86400 * 365)
    scope: str | None = Field(default=None, max_length=4096)
    id_token: str | None = Field(default=None, max_length=8192)
    provider_payload: Dict[str, Any] = Field(default_factory=dict)
    simulate_exchange: bool = False
    code_verifier: str | None = Field(default=None, max_length=8192)


class CommunicationAccountOAuthCompleteResponse(BaseModel):
    ok: bool
    action: str
    provider: str
    account: CommunicationChannelAccountOut
    detail: str | None = None


class CommunicationAccountOAuthRefreshRequest(BaseModel):
    expires_in: int | None = Field(default=3600, ge=60, le=86400 * 365)
    provider_payload: Dict[str, Any] = Field(default_factory=dict)
    simulate_refresh: bool = False


class CommunicationAccountSyncCursorPatch(BaseModel):
    cursor_key: str = Field(..., min_length=1, max_length=128)
    cursor_value: str | None = Field(default=None, max_length=4096)
    meta: Dict[str, Any] = Field(default_factory=dict)


class CommunicationAccountSyncCursorOut(BaseModel):
    account_id: str
    cursor_key: str
    cursor_value: str | None = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    updated_at: str | None = None


class TelegramWebhookSimulateRequest(BaseModel):
    channel_account_id: str = Field(..., max_length=36)
    update: Dict[str, Any] = Field(default_factory=dict)
    auto_assign: bool = True
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=120)
    linked_candidate_id: str | None = Field(default=None, max_length=36)
    linked_company_id: str | None = Field(default=None, max_length=36)


# ---------------------------------------------------------------------------
# Email worker + scheduler observability.
# ---------------------------------------------------------------------------


class CommunicationEmailWorkerDispatchRequest(BaseModel):
    limit: int = Field(default=25, ge=1, le=200)
    mark_delivered: bool = True


class CommunicationEmailWorkerPollRequest(BaseModel):
    only_account_id: str | None = Field(default=None, max_length=36)
    limit_per_account: int = Field(default=25, ge=1, le=200)


class CommunicationEmailWorkerPollResponse(BaseModel):
    polled_accounts: int
    supported_accounts: int
    ingested_messages: int
    created_threads: int
    skipped_messages: int
    unsupported_accounts: int
    items: List[Dict[str, Any]] = Field(default_factory=list)


class CommunicationSchedulerStatusOut(BaseModel):
    enabled: bool
    active: bool
    started_at: str | None = None
    stopped_at: str | None = None
    tick_seconds: int
    last_tick_started_at: str | None = None
    last_tick_finished_at: str | None = None
    last_tick_duration_ms: int | None = None
    last_tick_error: str | None = None
    last_tick_summary: Dict[str, Any] = Field(default_factory=dict)
    tenants: Dict[str, Any] = Field(default_factory=dict)


class CommunicationSchedulerRunNowResponse(BaseModel):
    ok: bool
    status: CommunicationSchedulerStatusOut


# ---------------------------------------------------------------------------
# Time-off requests (calendar/availability).
#
# Phase 2.1 (ADR-012, 2026-05-09): the legacy planner-event schemas
# (``CommunicationPlannerEventOut``, ``CommunicationPlannerEventCreate``,
# ``CommunicationPlannerEventPatch``, ``CommunicationPlannerEventListResponse``)
# were removed together with the corresponding HTTP routes. Activity
# create / update / list contracts live in
# ``backend/app/api/v1/reminders_v2.py`` and ``activities_v1.py``.
# ---------------------------------------------------------------------------


class TimeOffRequestOut(BaseModel):
    id: str
    tenant_id: str
    requester_user_id: str
    requester_label: str | None = None
    approver_user_id: str | None = None
    approver_label: str | None = None
    request_type: str
    status: str
    start_date: str
    end_date: str
    partial_day: str | None = None
    reason: str | None = None
    decision_note: str | None = None
    requested_at: datetime | None = None
    decided_at: datetime | None = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class TimeOffRequestListResponse(BaseModel):
    items: List[TimeOffRequestOut]
    total: int


class TimeOffRequestCreate(BaseModel):
    request_type: str = Field(default="vacation", max_length=32)
    start_date: str = Field(..., max_length=32)
    end_date: str = Field(..., max_length=32)
    partial_day: str | None = Field(default=None, max_length=16)
    reason: str | None = None
    approver_user_id: str | None = Field(default=None, max_length=36)
    approver_label: str | None = Field(default=None, max_length=255)
    payload: Dict[str, Any] = Field(default_factory=dict)


class TimeOffRequestDecision(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    decision_note: str | None = None


class TimeOffRequestCancel(BaseModel):
    reason: str | None = None
