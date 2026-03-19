from __future__ import annotations

import logging
import hashlib
import secrets
import re
import json
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.core.crypto import decrypt_secret, encrypt_secret, generate_secret
from backend.app.db.deps import get_db, get_db_with_tenant
from backend.app.models.communication import (
    CommunicationAllocationAudit,
    CommunicationChannelAccount,
    CommunicationCommandAudit,
    CommunicationMessage,
    CommunicationPlannerEvent,
    CommunicationTimeOffRequest,
    CommunicationThread,
)
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.vacancy import Vacancy
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.constants.stages import LABELS as CANDIDATE_STAGE_LABELS
from backend.app.services.communications_allocator import allocate_thread, preview_allocation
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.communications_email_imap import ImapClientConfig, poll_imap_messages, test_imap_connection
from backend.app.services.communications_email_oauth import OAuthMailboxPollError, poll_oauth_mailbox_messages
from backend.app.services.communications_email_oauth_send import OAuthMailboxSendError, send_oauth_email_message
from backend.app.services.communications_oauth import (
    OAuthProviderError,
    exchange_oauth_code_for_tokens,
    refresh_oauth_access_token,
)
from backend.app.services.communications_scheduler import run_scheduler_tick_once, scheduler_runtime_status
from backend.app.services.communications_meta import (
    MetaGraphConfig,
    meta_graph_get_object,
    normalize_meta_webhook,
    send_meta_text_message,
)
from backend.app.services.communications_telegram import (
    TelegramBotConfig,
    normalize_telegram_update,
    send_telegram_text,
    telegram_delete_webhook,
    telegram_get_me,
    telegram_get_webhook_info,
    telegram_set_webhook,
)
from backend.app.services.communications_whatsapp import (
    WhatsAppCloudConfig,
    normalize_whatsapp_webhook,
    send_whatsapp_text,
    whatsapp_get_phone_number_info,
)
from backend.app.services.communications_viber import (
    ViberBotConfig,
    normalize_viber_webhook,
    send_viber_text_message,
    viber_get_account_info,
)
from backend.app.services.tenant_email import send_email_for_tenant
from backend.app.core.settings import settings
from backend.app.modules.documents.crud import ensure_ruleset_seed
from backend.app.modules.documents.owner_summary import compute_owner_summary
from backend.app.services.document_ruleset import load_default_ruleset
from backend.app.services.ruleset_versioning import normalize_ruleset_payload
from backend.app.services.candidate_notifications import get_document_display_name
from backend.app.services.audit import log_activity
from backend.app.services.candidate_telegram_notifications import sync_candidate_ready_for_handoff_gate

router = APIRouter(prefix="/communications", tags=["communications"])
logger = logging.getLogger(__name__)


_CLOCK_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")


def _parse_clock_minutes(value: str) -> int:
    s = str(value or "").strip()
    if not _CLOCK_RE.match(s):
        raise ValueError("Invalid time format (expected HH:MM)")
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _normalize_working_hours(payload: Any) -> Dict[str, Any]:
    """
    Canonical weekly working hours contract (v1).

    Stored in User.extra under key `working_hours_v1`:
      {
        "tz": "Europe/Warsaw" | null,
        "days": [
          {"weekday": 0..6, "enabled": bool, "windows": [{"from":"09:00","to":"17:00"}]}
        ]
      }
    weekday: 0=Mon .. 6=Sun (ISO-like, aligned with frontend usage).
    """
    root = _as_dict(payload)
    tz = root.get("tz")
    tz_norm = str(tz).strip() if isinstance(tz, str) else None

    raw_days = root.get("days")
    days_in = raw_days if isinstance(raw_days, list) else []
    seen: set[int] = set()
    days_out: list[dict[str, Any]] = []
    for item in days_in:
        row = _as_dict(item)
        try:
            weekday = int(row.get("weekday"))
        except Exception:
            continue
        if weekday < 0 or weekday > 6:
            continue
        if weekday in seen:
            continue
        seen.add(weekday)
        enabled = bool(row.get("enabled", True))
        windows_in = row.get("windows") if isinstance(row.get("windows"), list) else []
        windows_out: list[dict[str, str]] = []
        for w in windows_in:
            wr = _as_dict(w)
            f = str(wr.get("from") or "").strip()
            t = str(wr.get("to") or "").strip()
            if not f or not t:
                continue
            fm = _parse_clock_minutes(f)
            tm = _parse_clock_minutes(t)
            if tm <= fm:
                continue
            windows_out.append({"from": f, "to": t})
        days_out.append({"weekday": weekday, "enabled": enabled, "windows": windows_out})
    days_out.sort(key=lambda x: int(x["weekday"]))
    return {"tz": tz_norm, "days": days_out}


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


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_dict(value: Any) -> Dict[str, Any]:
    return {**value} if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            normalized = text.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _deep_merge_dict(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = _as_dict(base)
    for key, value in _as_dict(patch).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge_dict(_as_dict(out.get(key)), _as_dict(value))
        else:
            out[key] = value
    return out


def _comm_settings_channels(tenant: Tenant | None) -> Dict[str, Any]:
    if tenant is None:
        return {}
    root = tenant.settings if isinstance(getattr(tenant, "settings", None), dict) else {}
    comm = root.get("communications")
    comm = comm if isinstance(comm, dict) else {}
    channels = comm.get("channels")
    return channels if isinstance(channels, dict) else {}


def _comm_settings_root(tenant: Tenant | None) -> Dict[str, Any]:
    if tenant is None:
        return {}
    root = tenant.settings if isinstance(getattr(tenant, "settings", None), dict) else {}
    comm = root.get("communications")
    return comm if isinstance(comm, dict) else {}


def _tenant_sla_escalation_targets(tenant: Tenant | None) -> set[str]:
    comm = _comm_settings_root(tenant)
    sla = comm.get("sla")
    sla = sla if isinstance(sla, dict) else {}
    raw = sla.get("escalationTargets")
    if not isinstance(raw, list):
        return set()
    out: set[str] = set()
    for item in raw:
        value = str(item or "").strip()
        if value:
            out.add(value)
    return out


def _tenant_comm_allowed_roles(tenant: Tenant | None) -> set[str]:
    comm = _comm_settings_root(tenant)
    access = comm.get("access")
    access = access if isinstance(access, dict) else {}
    roles = access.get("roles")
    roles = roles if isinstance(roles, dict) else {}
    out: set[str] = set()
    for _, value in roles.items():
        if not isinstance(value, list):
            continue
        for role in value:
            normalized = str(role or "").strip().lower()
            if normalized:
                out.add(normalized)
    return out


def _channel_response_sla_minutes(tenant: Tenant | None, channel: str) -> int | None:
    channels_cfg = _comm_settings_channels(tenant)
    rows = channels_cfg.get("channels")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("key") or "").strip().lower() != str(channel or "").strip().lower():
                continue
            try:
                return max(1, int(row.get("responseSlaMinutes") or 0))
            except Exception:
                return None
    return None


def _apply_thread_sla_policy_from_message(thread: CommunicationThread, msg: CommunicationMessage, tenant: Tenant | None) -> None:
    if msg.is_internal_note:
        return
    thread_meta_current = _as_dict(thread.thread_meta)
    sla_policy_current = _as_dict(thread_meta_current.get("sla_policy"))
    muted = bool(sla_policy_current.get("muted") or thread_meta_current.get("sla_muted"))
    if muted:
        thread.sla_due_at = None
        return
    no_reply_needed = bool(sla_policy_current.get("no_reply_needed") or thread_meta_current.get("no_reply_needed"))
    if no_reply_needed:
        thread.sla_due_at = None
        return
    if msg.direction == "inbound":
        sla_minutes = _channel_response_sla_minutes(tenant, thread.channel)
        if sla_minutes and sla_minutes > 0:
            base_ts = msg.sent_at or msg.delivered_at or msg.created_at or _now_utc()
            thread.sla_due_at = base_ts + timedelta(minutes=sla_minutes)
            thread_meta = _as_dict(thread.thread_meta)
            thread_meta["sla_policy"] = {
                **_as_dict(thread_meta.get("sla_policy")),
                "response_sla_minutes": sla_minutes,
                "channel": thread.channel,
                "last_started_at": base_ts.isoformat(),
                "last_due_at": thread.sla_due_at.isoformat() if thread.sla_due_at else None,
            }
            thread.thread_meta = thread_meta
        return
    if msg.direction == "outbound":
        if thread.sla_due_at is not None:
            thread_meta = _as_dict(thread.thread_meta)
            thread_meta["sla_policy"] = {
                **_as_dict(thread_meta.get("sla_policy")),
                "last_replied_at": (msg.sent_at or msg.created_at or _now_utc()).isoformat(),
                "last_cleared_due_at": thread.sla_due_at.isoformat(),
            }
            thread.thread_meta = thread_meta
        thread.sla_due_at = None


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


class CommunicationThreadPatch(BaseModel):
    subject: str | None = Field(default=None, max_length=512)
    status: str | None = Field(default=None, max_length=32)
    assignee_id: str | None = Field(default=None, max_length=36)
    queue_assigned_by: str | None = Field(default=None, max_length=32)
    priority: str | None = Field(default=None, max_length=16)
    is_archived: bool | None = None
    unread_count: int | None = Field(default=None, ge=0)
    participants_json: Dict[str, Any] | None = None
    tags_json: List[Any] | None = None
    thread_meta: Dict[str, Any] | None = None


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


class CommunicationChannelAccountPatch(BaseModel):
    account_label: str | None = Field(default=None, min_length=1, max_length=255)
    external_account_ref: str | None = Field(default=None, max_length=255)
    inbox_address: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    settings_json: Dict[str, Any] | None = None


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


class CommunicationAccountActionResponse(BaseModel):
    ok: bool
    action: str
    status: str
    account: CommunicationChannelAccountOut
    detail: str | None = None


class CommunicationAccountOAuthStartRequest(BaseModel):
    redirect_uri: str | None = Field(default=None, max_length=2048)
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


class CommunicationPlannerEventOut(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: str | None = None
    kind: str
    status: str
    priority: str
    start_at: datetime
    end_at: datetime | None = None
    all_day: bool
    owner_id: str | None = None
    assignee_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    linked_candidate_id: str | None = None
    linked_company_id: str | None = None
    source: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CommunicationPlannerEventListResponse(BaseModel):
    items: List[CommunicationPlannerEventOut]
    total: int


class CommunicationPlannerEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    kind: str = Field(default="task", max_length=32)
    status: str = Field(default="planned", max_length=32)
    priority: str = Field(default="normal", max_length=16)
    start_at: datetime
    end_at: datetime | None = None
    all_day: bool = False
    assignee_id: str | None = Field(default=None, max_length=36)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=120)
    linked_candidate_id: str | None = Field(default=None, max_length=36)
    linked_company_id: str | None = Field(default=None, max_length=36)
    source: str = Field(default="manual", max_length=32)
    payload: Dict[str, Any] = Field(default_factory=dict)


class CommunicationPlannerEventPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    kind: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    priority: str | None = Field(default=None, max_length=16)
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    assignee_id: str | None = Field(default=None, max_length=36)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=120)
    linked_candidate_id: str | None = Field(default=None, max_length=36)
    linked_company_id: str | None = Field(default=None, max_length=36)
    payload: Dict[str, Any] | None = None


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


def _planner_event_out(row: CommunicationPlannerEvent) -> CommunicationPlannerEventOut:
    return CommunicationPlannerEventOut(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        title=row.title,
        description=row.description,
        kind=row.kind,
        status=row.status,
        priority=row.priority,
        start_at=row.start_at,
        end_at=row.end_at,
        all_day=bool(row.all_day),
        owner_id=row.owner_id,
        assignee_id=row.assignee_id,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        linked_candidate_id=row.linked_candidate_id,
        linked_company_id=row.linked_company_id,
        source=row.source,
        payload=_as_dict(row.payload),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


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


def _validate_iso_date_range(start_date: str, end_date: str) -> None:
    try:
        start = str(start_date).strip()
        end = str(end_date).strip()
        if not start or not end:
            raise ValueError("empty")
        if end < start:
            raise ValueError("end_before_start")
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid date range")


def _partial_day_blocks_now(partial_day: str | None, now_local: datetime, payload: Dict[str, Any] | None = None) -> bool:
    token = str(partial_day or "").strip().lower()
    payload = payload if isinstance(payload, dict) else {}
    time_window = _as_dict(payload.get("time_window"))
    try:
        from_raw = str(time_window.get("from") or "").strip()
        to_raw = str(time_window.get("to") or "").strip()
        if from_raw and to_raw and ":" in from_raw and ":" in to_raw:
            fh, fm = [int(x) for x in from_raw.split(":", 1)]
            th, tm = [int(x) for x in to_raw.split(":", 1)]
            cur = now_local.hour * 60 + now_local.minute
            start_min = fh * 60 + fm
            end_min = th * 60 + tm
            if 0 <= start_min <= 1439 and 0 <= end_min <= 1439:
                return start_min <= cur <= end_min
    except Exception:
        pass
    if not token:
        return True
    hour = int(now_local.hour)
    if token in {"am", "first_half", "morning"}:
        return hour < 13
    if token in {"pm", "second_half", "afternoon"}:
        return hour >= 13
    return True


async def _sync_manager_queue_availability_from_time_off(
    db: AsyncSession,
    *,
    tenant: Tenant,
    user_id: str,
    now_utc: datetime | None = None,
) -> bool:
    now_utc = now_utc or _now_utc()
    today = now_utc.date().isoformat()
    current_settings = tenant.settings if isinstance(getattr(tenant, "settings", None), dict) else {}
    comm = _as_dict(current_settings.get("communications")).copy()
    queue = _as_dict(comm.get("managerQueue")).copy()
    items = queue.get("items")
    if not isinstance(items, list) or not items:
        return False

    stmt = sa.select(CommunicationTimeOffRequest).where(
        CommunicationTimeOffRequest.tenant_id == str(tenant.id),
        CommunicationTimeOffRequest.requester_user_id == str(user_id),
        CommunicationTimeOffRequest.status == "approved",
        CommunicationTimeOffRequest.start_date <= today,
        CommunicationTimeOffRequest.end_date >= today,
    ).order_by(sa.desc(CommunicationTimeOffRequest.updated_at))
    rows = (await db.execute(stmt)).scalars().all()
    active_now = None
    for row in rows:
        if _partial_day_blocks_now(row.partial_day, now_utc, _as_dict(row.payload)):
            active_now = row
            break

    changed = False
    next_items: List[Dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict) or str(raw.get("managerId") or "") != str(user_id):
            next_items.append(raw)
            continue
        item = dict(raw)
        availability = _as_dict(item.get("availability")).copy()
        note = str(availability.get("note") or "")
        auto_prefix = "[time-off-auto]"
        if active_now is not None:
            desired_note = f"{auto_prefix} approved {active_now.request_type} {active_now.start_date}..{active_now.end_date}"
            if active_now.partial_day:
                desired_note += f" ({active_now.partial_day})"
            if availability.get("state") != "offline" or note != desired_note:
                availability["state"] = "offline"
                availability["note"] = desired_note
                changed = True
        else:
            if availability.get("state") == "offline" and note.startswith(auto_prefix):
                availability["state"] = "available"
                availability["note"] = ""
                changed = True
        item["availability"] = availability
        next_items.append(item)

    if not changed:
        return False
    queue["items"] = next_items
    comm["managerQueue"] = queue
    updated_tenant_settings = dict(current_settings)
    updated_tenant_settings["communications"] = comm
    tenant.settings = updated_tenant_settings
    db.add(tenant)
    return True


async def _get_thread_or_404(db: AsyncSession, tenant_id: str, thread_id: str) -> CommunicationThread:
    thread = await db.get(CommunicationThread, thread_id)
    if thread is None or str(thread.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


async def _get_tenant_or_404(db: AsyncSession, tenant_id: str) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _feature_for_channel(channel: str | None) -> str:
    ch = str(channel or "").strip().lower()
    return "email" if ch == "email" else "messages"


def _message_templates_for_user(
    tenant: Tenant,
    *,
    user_id: str | None,
    target: str,
) -> List[CommunicationMessageTemplateOut]:
    comm = _comm_settings_root(tenant)
    block = comm.get("messageTemplates")
    rows = block.get("items") if isinstance(block, dict) else None
    if not isinstance(rows, list):
        return []

    normalized_target = str(target or "messages").strip().lower()
    out: List[CommunicationMessageTemplateOut] = []
    for idx, raw in enumerate(rows):
        if not isinstance(raw, dict):
            continue
        enabled = bool(raw.get("enabled", True))
        if not enabled:
            continue
        tpl_target = str(raw.get("target") or "messages").strip().lower()
        if tpl_target not in {"messages", "email", "both"}:
            tpl_target = "messages"
        if tpl_target != "both" and tpl_target != normalized_target:
            continue

        visibility = str(raw.get("visibility") or "private").strip().lower()
        if visibility not in {"private", "company"}:
            visibility = "private"
        owner_user_id = str(raw.get("ownerUserId") or raw.get("owner_user_id") or "").strip() or None
        if visibility == "private" and (not owner_user_id or not user_id or owner_user_id != user_id):
            continue

        out.append(
            CommunicationMessageTemplateOut(
                id=str(raw.get("id") or f"msg_tpl_{idx + 1}"),
                label=str(raw.get("label") or f"Template {idx + 1}"),
                body=str(raw.get("body") or ""),
                visibility=visibility,
                target=tpl_target,
                owner_user_id=owner_user_id,
                enabled=enabled,
            )
        )
    return out


async def _require_comm_feature(
    db: AsyncSession,
    *,
    tenant_id: str,
    current_user: UserCtx,
    feature: str,
) -> Tenant:
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=feature)  # type: ignore[arg-type]
    return tenant


async def _require_any_comm_feature(
    db: AsyncSession,
    *,
    tenant_id: str,
    current_user: UserCtx,
    features: List[str],
) -> Tenant:
    tenant = await _get_tenant_or_404(db, tenant_id)
    allowed = False
    for feature in features:
        try:
            assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=feature)  # type: ignore[arg-type]
            allowed = True
            break
        except HTTPException:
            continue
    if not allowed:
        raise HTTPException(status_code=403, detail="Communications access denied")
    return tenant


async def _find_thread_for_inbound_email(
    db: AsyncSession,
    *,
    tenant_id: str,
    channel_account_id: str | None,
    provider_thread_ref: str | None,
    subject: str | None,
    from_address: str | None,
) -> CommunicationThread | None:
    if provider_thread_ref:
        stmt = sa.select(CommunicationThread).where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.channel == "email",
            CommunicationThread.channel_thread_ref == provider_thread_ref,
        ).limit(1)
        row = (await db.execute(stmt)).scalars().first()
        if row:
            return row

    # Fallback heuristic for MVP testing (same account + subject + sender among recent threads)
    if subject and channel_account_id:
        like_subject = subject.strip()
        if like_subject:
            stmt = (
                sa.select(CommunicationThread)
                .where(
                    CommunicationThread.tenant_id == tenant_id,
                    CommunicationThread.channel == "email",
                    CommunicationThread.channel_account_id == channel_account_id,
                    CommunicationThread.subject == like_subject,
                    CommunicationThread.is_archived.is_(False),
                )
                .order_by(sa.desc(sa.func.coalesce(CommunicationThread.last_message_at, CommunicationThread.updated_at)))
                .limit(5)
            )
            candidates = (await db.execute(stmt)).scalars().all()
            normalized_from = (from_address or "").strip().lower()
            for th in candidates:
                participants = _as_dict(th.participants_json)
                senders = participants.get("senders")
                if isinstance(senders, list) and normalized_from:
                    if any(str(x).strip().lower() == normalized_from for x in senders):
                        return th
            if candidates:
                return candidates[0]
    return None


async def _find_thread_for_inbound_channel(
    db: AsyncSession,
    *,
    tenant_id: str,
    channel: str,
    channel_account_id: str | None,
    provider_thread_ref: str | None,
    sender_address: str | None,
) -> CommunicationThread | None:
    ref = (provider_thread_ref or "").strip()
    if ref:
        stmt = sa.select(CommunicationThread).where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.channel == channel,
            CommunicationThread.channel_thread_ref == ref,
        ).limit(1)
        found = (await db.execute(stmt)).scalars().first()
        if found:
            return found

    # Fallback: same channel + account + sender in recent active threads
    if not sender_address:
        return None
    stmt = (
        sa.select(CommunicationThread)
        .where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.channel == channel,
            CommunicationThread.is_archived.is_(False),
        )
        .order_by(sa.desc(sa.func.coalesce(CommunicationThread.last_message_at, CommunicationThread.updated_at)))
        .limit(20)
    )
    if channel_account_id:
        stmt = stmt.where(CommunicationThread.channel_account_id == channel_account_id)
    rows = (await db.execute(stmt)).scalars().all()
    normalized_sender = sender_address.strip().lower()
    for th in rows:
        participants = _as_dict(th.participants_json)
        senders = participants.get("senders")
        if isinstance(senders, list) and any(str(x).strip().lower() == normalized_sender for x in senders):
            return th
    return None


async def _ingest_email_outbound_from_mailbox(
    db: AsyncSession,
    *,
    tenant_id: str,
    channel_account_id: str,
    provider: str,
    provider_thread_ref: str | None,
    external_message_ref: str | None,
    subject: str | None,
    from_address: str | None,
    to_address: str | None,
    to_name: str | None,
    text: str | None,
    html: str | None,
    headers: Dict[str, Any],
    payload: Dict[str, Any],
    sent_at: datetime | None,
    tenant: Tenant,
) -> Tuple[bool, bool]:
    if external_message_ref:
        existing_msg_stmt = sa.select(CommunicationMessage).where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.channel == "email",
            CommunicationMessage.external_message_ref == external_message_ref,
        ).limit(1)
        existing_msg = (await db.execute(existing_msg_stmt)).scalars().first()
        if existing_msg:
            return False, True

    thread = await _find_thread_for_inbound_email(
        db,
        tenant_id=tenant_id,
        channel_account_id=channel_account_id,
        provider_thread_ref=provider_thread_ref,
        subject=subject,
        from_address=to_address,
    )
    created_thread = False
    if thread is None:
        participants = {
            "senders": [from_address] if from_address else [],
            "recipients": [to_address] if to_address else [],
            "cc": [],
            "bcc": [],
        }
        thread = CommunicationThread(
            tenant_id=tenant_id,
            channel="email",
            channel_account_id=channel_account_id,
            channel_thread_ref=provider_thread_ref,
            subject=subject,
            status="open",
            direction_hint="outbound",
            priority="normal",
            participants_json=participants,
            tags_json=[],
            thread_meta={"provider": provider, "mailbox_source": "sent"},
        )
        db.add(thread)
        await db.flush()
        created_thread = True
    else:
        participants = _as_dict(thread.participants_json)
        recipients = participants.get("recipients")
        if not isinstance(recipients, list):
            recipients = []
        if to_address and to_address not in recipients:
            recipients.append(to_address)
        participants["recipients"] = recipients
        senders = participants.get("senders")
        if not isinstance(senders, list):
            senders = []
        if from_address and from_address not in senders:
            senders.append(from_address)
        participants["senders"] = senders
        thread.participants_json = participants
        if subject and not thread.subject:
            thread.subject = subject

    ts = sent_at or _now_utc()
    msg = CommunicationMessage(
        tenant_id=tenant_id,
        thread_id=str(thread.id),
        channel="email",
        message_type="email",
        direction="outbound",
        sender_type="user",
        sender_label=None,
        sender_address=from_address,
        recipient_type="external",
        recipient_label=to_name,
        recipient_address=to_address,
        subject=subject,
        body_text=text,
        body_html=html,
        attachments_json=[],
        payload={**(payload or {}), "headers": headers or {}, "provider": provider, "mailbox_source": "sent"},
        external_message_ref=external_message_ref,
        delivery_status="delivered",
        sent_at=ts,
        delivered_at=ts,
        read_at=None,
        is_internal_note=False,
    )
    db.add(msg)
    await db.flush()
    _touch_thread_from_message(thread, msg, tenant=tenant)
    return created_thread, False


def _derive_account_status(account: CommunicationChannelAccount) -> Tuple[str, str | None]:
    settings = _as_dict(account.settings_json)
    sync = _as_dict(settings.get("sync"))
    connection = _as_dict(settings.get("connection"))
    if not bool(account.is_active):
        return "disabled", "Account disabled"
    if str(connection.get("status") or "") == "error":
        return "error", str(connection.get("last_error") or "Connection error")
    if str(sync.get("status") or "") == "error":
        return "error", str(sync.get("last_error") or "Sync error")
    if connection.get("last_test_at"):
        return "connected", None
    return "not_tested", "Connection was not tested yet"


def _sanitize_account_settings_for_out(settings_json: Any) -> Dict[str, Any]:
    settings = _as_dict(settings_json)
    out = {**settings}
    imap_cfg = _as_dict(out.get("imap"))
    if imap_cfg:
        imap_out = {**imap_cfg}
        if "password" in imap_out:
            imap_out.pop("password", None)
        imap_out["has_password"] = bool(imap_cfg.get("password_encrypted") or imap_cfg.get("password"))
        out["imap"] = imap_out
    telegram_cfg = _as_dict(out.get("telegram"))
    if telegram_cfg:
        tg_out = {**telegram_cfg}
        tg_out.pop("bot_token", None)
        tg_out["has_bot_token"] = bool(telegram_cfg.get("bot_token_encrypted") or telegram_cfg.get("bot_token"))
        out["telegram"] = tg_out
    whatsapp_cfg = _as_dict(out.get("whatsapp"))
    if whatsapp_cfg:
        wa_out = {**whatsapp_cfg}
        wa_out.pop("access_token", None)
        wa_out["has_access_token"] = bool(whatsapp_cfg.get("access_token_encrypted") or whatsapp_cfg.get("access_token"))
        out["whatsapp"] = wa_out
    viber_cfg = _as_dict(out.get("viber"))
    if viber_cfg:
        viber_out = {**viber_cfg}
        viber_out.pop("bot_token", None)
        viber_out["has_bot_token"] = bool(viber_cfg.get("bot_token_encrypted") or viber_cfg.get("bot_token"))
        out["viber"] = viber_out
    messenger_cfg = _as_dict(out.get("messenger"))
    if messenger_cfg:
        messenger_out = {**messenger_cfg}
        messenger_out.pop("access_token", None)
        messenger_out.pop("app_secret", None)
        messenger_out["has_access_token"] = bool(messenger_cfg.get("access_token_encrypted") or messenger_cfg.get("access_token"))
        messenger_out["has_app_secret"] = bool(messenger_cfg.get("app_secret_encrypted") or messenger_cfg.get("app_secret"))
        out["messenger"] = messenger_out
    instagram_cfg = _as_dict(out.get("instagram"))
    if instagram_cfg:
        instagram_out = {**instagram_cfg}
        instagram_out.pop("access_token", None)
        instagram_out["has_access_token"] = bool(instagram_cfg.get("access_token_encrypted") or instagram_cfg.get("access_token"))
        out["instagram"] = instagram_out
    oauth_cfg = _as_dict(out.get("oauth"))
    if oauth_cfg:
        oauth_out = {**oauth_cfg}
        oauth_out.pop("access_token", None)
        oauth_out.pop("refresh_token", None)
        oauth_out.pop("id_token", None)
        oauth_out.pop("client_secret", None)
        oauth_out["has_access_token"] = bool(oauth_cfg.get("access_token_encrypted") or oauth_cfg.get("access_token"))
        oauth_out["has_refresh_token"] = bool(oauth_cfg.get("refresh_token_encrypted") or oauth_cfg.get("refresh_token"))
        oauth_out["has_id_token"] = bool(oauth_cfg.get("id_token_encrypted") or oauth_cfg.get("id_token"))
        oauth_out["has_client_secret"] = bool(oauth_cfg.get("client_secret_encrypted") or oauth_cfg.get("client_secret"))
        out["oauth"] = oauth_out
    return out


def _account_out(account: CommunicationChannelAccount) -> CommunicationChannelAccountOut:
    return CommunicationChannelAccountOut(
        id=str(account.id),
        channel=account.channel,
        account_label=account.account_label,
        external_account_ref=account.external_account_ref,
        inbox_address=account.inbox_address,
        is_active=bool(account.is_active),
        settings_json=_sanitize_account_settings_for_out(account.settings_json),
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def _normalize_account_settings_for_store(settings_json: Any) -> Dict[str, Any]:
    settings = _as_dict(settings_json)
    out = {**settings}
    imap_cfg = _as_dict(out.get("imap"))
    if imap_cfg:
        imap_mut = {**imap_cfg}
        raw_password = imap_mut.pop("password", None)
        if raw_password is not None:
            raw_password_text = str(raw_password).strip()
            if raw_password_text:
                imap_mut["password_encrypted"] = encrypt_secret(raw_password_text)
        out["imap"] = imap_mut
    telegram_cfg = _as_dict(out.get("telegram"))
    if telegram_cfg:
        tg_mut = {**telegram_cfg}
        raw_token = tg_mut.pop("bot_token", None)
        if raw_token is not None:
            raw_token_text = str(raw_token).strip()
            if raw_token_text:
                tg_mut["bot_token_encrypted"] = encrypt_secret(raw_token_text)
        out["telegram"] = tg_mut
    whatsapp_cfg = _as_dict(out.get("whatsapp"))
    if whatsapp_cfg:
        wa_mut = {**whatsapp_cfg}
        raw_access = wa_mut.pop("access_token", None)
        if raw_access is not None:
            raw_access_text = str(raw_access).strip()
            if raw_access_text:
                wa_mut["access_token_encrypted"] = encrypt_secret(raw_access_text)
        out["whatsapp"] = wa_mut
    viber_cfg = _as_dict(out.get("viber"))
    if viber_cfg:
        viber_mut = {**viber_cfg}
        raw_token = viber_mut.pop("bot_token", None)
        if raw_token is not None:
            raw_token_text = str(raw_token).strip()
            if raw_token_text:
                viber_mut["bot_token_encrypted"] = encrypt_secret(raw_token_text)
        out["viber"] = viber_mut
    messenger_cfg = _as_dict(out.get("messenger"))
    if messenger_cfg:
        messenger_mut = {**messenger_cfg}
        raw_access = messenger_mut.pop("access_token", None)
        raw_secret = messenger_mut.pop("app_secret", None)
        if raw_access is not None:
            raw_access_text = str(raw_access).strip()
            if raw_access_text:
                messenger_mut["access_token_encrypted"] = encrypt_secret(raw_access_text)
        if raw_secret is not None:
            raw_secret_text = str(raw_secret).strip()
            if raw_secret_text:
                messenger_mut["app_secret_encrypted"] = encrypt_secret(raw_secret_text)
        out["messenger"] = messenger_mut
    instagram_cfg = _as_dict(out.get("instagram"))
    if instagram_cfg:
        instagram_mut = {**instagram_cfg}
        raw_access = instagram_mut.pop("access_token", None)
        if raw_access is not None:
            raw_access_text = str(raw_access).strip()
            if raw_access_text:
                instagram_mut["access_token_encrypted"] = encrypt_secret(raw_access_text)
        out["instagram"] = instagram_mut
    oauth_cfg = _as_dict(out.get("oauth"))
    if oauth_cfg:
        oauth_mut = {**oauth_cfg}
        raw_access = oauth_mut.pop("access_token", None)
        raw_refresh = oauth_mut.pop("refresh_token", None)
        raw_id = oauth_mut.pop("id_token", None)
        raw_client_secret = oauth_mut.pop("client_secret", None)
        if raw_access is not None:
            raw_access_text = str(raw_access).strip()
            if raw_access_text:
                oauth_mut["access_token_encrypted"] = encrypt_secret(raw_access_text)
        if raw_refresh is not None:
            raw_refresh_text = str(raw_refresh).strip()
            if raw_refresh_text:
                oauth_mut["refresh_token_encrypted"] = encrypt_secret(raw_refresh_text)
        if raw_id is not None:
            raw_id_text = str(raw_id).strip()
            if raw_id_text:
                oauth_mut["id_token_encrypted"] = encrypt_secret(raw_id_text)
        if raw_client_secret is not None:
            raw_client_secret_text = str(raw_client_secret).strip()
            if raw_client_secret_text:
                oauth_mut["client_secret_encrypted"] = encrypt_secret(raw_client_secret_text)
        out["oauth"] = oauth_mut
    return out


def _oauth_client_secret(oauth_json: Dict[str, Any]) -> str | None:
    encrypted = str(oauth_json.get("client_secret_encrypted") or "").strip()
    if encrypted:
        return decrypt_secret(encrypted) or None
    plain = str(oauth_json.get("client_secret") or "").strip()
    return plain or None


def _oauth_refresh_token(oauth_json: Dict[str, Any]) -> str | None:
    encrypted = str(oauth_json.get("refresh_token_encrypted") or "").strip()
    if encrypted:
        return decrypt_secret(encrypted) or None
    plain = str(oauth_json.get("refresh_token") or "").strip()
    return plain or None


def _oauth_access_token(oauth_json: Dict[str, Any]) -> str | None:
    encrypted = str(oauth_json.get("access_token_encrypted") or "").strip()
    if encrypted:
        return decrypt_secret(encrypted) or None
    plain = str(oauth_json.get("access_token") or "").strip()
    return plain or None


def _oauth_expires_soon(oauth_json: Dict[str, Any], *, skew_seconds: int = 120) -> bool:
    raw = str(oauth_json.get("expires_at") or "").strip()
    if not raw:
        return False
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt <= (_now_utc() + timedelta(seconds=skew_seconds))
    except Exception:
        return False


def _imap_config_from_account_settings(account: CommunicationChannelAccount) -> ImapClientConfig | None:
    settings = _as_dict(account.settings_json)
    imap_json = _as_dict(settings.get("imap"))
    host = str(imap_json.get("host") or "").strip()
    user = str(imap_json.get("user") or "").strip()
    if not host or not user:
        return None
    password = ""
    if imap_json.get("password_encrypted"):
        password = decrypt_secret(str(imap_json.get("password_encrypted") or "")) or ""
    elif imap_json.get("password"):
        password = str(imap_json.get("password") or "")
    port = int(imap_json.get("port") or (993 if bool(imap_json.get("use_ssl", True)) else 143))
    return ImapClientConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        use_ssl=bool(imap_json.get("use_ssl", True)),
        folder=str(imap_json.get("folder") or "INBOX"),
        search_criteria=str(imap_json.get("search_criteria") or "UNSEEN"),
        mark_seen=bool(imap_json.get("mark_seen", False)),
        timeout_seconds=max(3, int(imap_json.get("timeout_seconds") or 15)),
    )


def _telegram_config_from_account_settings(account: CommunicationChannelAccount) -> TelegramBotConfig | None:
    settings = _as_dict(account.settings_json)
    tg_json = _as_dict(settings.get("telegram"))
    token = ""
    if tg_json.get("bot_token_encrypted"):
        token = decrypt_secret(str(tg_json.get("bot_token_encrypted") or "")) or ""
    elif tg_json.get("bot_token"):
        token = str(tg_json.get("bot_token") or "")
    token = token.strip()
    if not token:
        return None
    return TelegramBotConfig(
        bot_token=token,
        timeout_seconds=max(3, int(tg_json.get("timeout_seconds") or 15)),
    )


def _whatsapp_config_from_account_settings(account: CommunicationChannelAccount) -> WhatsAppCloudConfig | None:
    settings = _as_dict(account.settings_json)
    wa_json = _as_dict(settings.get("whatsapp"))
    access_token = ""
    if wa_json.get("access_token_encrypted"):
        access_token = decrypt_secret(str(wa_json.get("access_token_encrypted") or "")) or ""
    elif wa_json.get("access_token"):
        access_token = str(wa_json.get("access_token") or "")
    phone_number_id = str(wa_json.get("phone_number_id") or account.external_account_ref or "").strip()
    api_version = str(wa_json.get("api_version") or "v20.0").strip() or "v20.0"
    access_token = access_token.strip()
    if not access_token or not phone_number_id:
        return None
    return WhatsAppCloudConfig(
        access_token=access_token,
        phone_number_id=phone_number_id,
        api_version=api_version,
        timeout_seconds=max(3, int(wa_json.get("timeout_seconds") or 15)),
    )


def _viber_config_from_account_settings(account: CommunicationChannelAccount) -> ViberBotConfig | None:
    settings = _as_dict(account.settings_json)
    viber_json = _as_dict(settings.get("viber"))
    token = ""
    if viber_json.get("bot_token_encrypted"):
        token = decrypt_secret(str(viber_json.get("bot_token_encrypted") or "")) or ""
    elif viber_json.get("bot_token"):
        token = str(viber_json.get("bot_token") or "")
    token = token.strip()
    if not token:
        return None
    return ViberBotConfig(
        bot_token=token,
        timeout_seconds=max(3, int(viber_json.get("timeout_seconds") or 15)),
    )


def _messenger_graph_config_from_account_settings(account: CommunicationChannelAccount) -> tuple[MetaGraphConfig | None, str]:
    settings = _as_dict(account.settings_json)
    messenger_json = _as_dict(settings.get("messenger"))
    access_token = ""
    if messenger_json.get("access_token_encrypted"):
        access_token = decrypt_secret(str(messenger_json.get("access_token_encrypted") or "")) or ""
    elif messenger_json.get("access_token"):
        access_token = str(messenger_json.get("access_token") or "")
    access_token = access_token.strip()
    page_id = str(messenger_json.get("page_id") or account.external_account_ref or "").strip()
    api_version = str(messenger_json.get("api_version") or "v20.0").strip() or "v20.0"
    if not access_token or not page_id:
        return None, page_id
    return (
        MetaGraphConfig(
            access_token=access_token,
            api_version=api_version,
            timeout_seconds=max(3, int(messenger_json.get("timeout_seconds") or 15)),
        ),
        page_id,
    )


def _instagram_graph_config_from_account_settings(account: CommunicationChannelAccount) -> tuple[MetaGraphConfig | None, str]:
    settings = _as_dict(account.settings_json)
    instagram_json = _as_dict(settings.get("instagram"))
    access_token = ""
    if instagram_json.get("access_token_encrypted"):
        access_token = decrypt_secret(str(instagram_json.get("access_token_encrypted") or "")) or ""
    elif instagram_json.get("access_token"):
        access_token = str(instagram_json.get("access_token") or "")
    access_token = access_token.strip()
    account_id = str(instagram_json.get("account_id") or account.external_account_ref or "").strip()
    api_version = str(instagram_json.get("api_version") or "v20.0").strip() or "v20.0"
    if not access_token or not account_id:
        return None, account_id
    return (
        MetaGraphConfig(
            access_token=access_token,
            api_version=api_version,
            timeout_seconds=max(3, int(instagram_json.get("timeout_seconds") or 15)),
        ),
        account_id,
    )


def _oauth_provider_for_account(account: CommunicationChannelAccount) -> str:
    settings = _as_dict(account.settings_json)
    oauth_json = _as_dict(settings.get("oauth"))
    provider = str(oauth_json.get("provider") or settings.get("provider") or account.channel or "").strip().lower()
    if provider in {"google", "gmail"}:
        return "gmail"
    if provider in {"microsoft", "ms", "graph", "microsoft_graph", "office365"}:
        return "microsoft_graph"
    return provider or "unknown"


def _oauth_authorize_url_for_provider(provider: str) -> str:
    if provider == "gmail":
        return "https://accounts.google.com/o/oauth2/v2/auth"
    if provider == "microsoft_graph":
        return "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    return "https://example.com/oauth/authorize"


def _oauth_default_scopes(provider: str) -> List[str]:
    if provider == "gmail":
        return [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ]
    if provider == "microsoft_graph":
        return [
            "offline_access",
            "User.Read",
            "Mail.Read",
            "Mail.Send",
        ]
    return ["openid", "email"]


def _build_oauth_auth_url(
    *,
    provider: str,
    client_id: str | None,
    redirect_uri: str | None,
    scopes: List[str],
    state: str,
    force_consent: bool,
) -> str:
    base = _oauth_authorize_url_for_provider(provider)
    safe_client_id = client_id or "missing_client_id"
    safe_redirect_uri = redirect_uri or "https://hostflow.cc/app/email"
    scope_joined = " ".join([s for s in scopes if isinstance(s, str) and s.strip()]) or "openid email"
    prompt = "consent" if force_consent else "select_account"
    query = urlencode(
        {
            "client_id": safe_client_id,
            "redirect_uri": safe_redirect_uri,
            "response_type": "code",
            "scope": scope_joined,
            "state": state,
            "prompt": prompt,
        }
    )
    return f"{base}?{query}"


async def _find_telegram_account_by_webhook_secret(
    db: AsyncSession,
    *,
    webhook_secret: str,
) -> CommunicationChannelAccount | None:
    secret = (webhook_secret or "").strip()
    if not secret:
        return None
    stmt = sa.select(CommunicationChannelAccount).where(
        CommunicationChannelAccount.channel == "telegram",
        CommunicationChannelAccount.is_active.is_(True),
    )
    rows = (await db.execute(stmt)).scalars().all()
    for account in rows:
        settings = _as_dict(account.settings_json)
        tg = _as_dict(settings.get("telegram"))
        if str(tg.get("webhook_secret") or "").strip() == secret:
            return account
    return None


async def _find_whatsapp_account_by_webhook_secret(
    db: AsyncSession,
    *,
    webhook_secret: str,
) -> CommunicationChannelAccount | None:
    secret = (webhook_secret or "").strip()
    if not secret:
        return None
    stmt = sa.select(CommunicationChannelAccount).where(
        CommunicationChannelAccount.channel == "whatsapp",
        CommunicationChannelAccount.is_active.is_(True),
    )
    rows = (await db.execute(stmt)).scalars().all()
    for account in rows:
        settings = _as_dict(account.settings_json)
        wa = _as_dict(settings.get("whatsapp"))
        if str(wa.get("webhook_secret") or "").strip() == secret:
            return account
    return None


async def _find_channel_account_by_webhook_secret(
    db: AsyncSession,
    *,
    channel: str,
    config_key: str,
    webhook_secret: str,
) -> CommunicationChannelAccount | None:
    secret = (webhook_secret or "").strip()
    if not secret:
        return None
    stmt = sa.select(CommunicationChannelAccount).where(
        CommunicationChannelAccount.channel == channel,
        CommunicationChannelAccount.is_active.is_(True),
    )
    rows = (await db.execute(stmt)).scalars().all()
    for account in rows:
        settings = _as_dict(account.settings_json)
        cfg = _as_dict(settings.get(config_key))
        if str(cfg.get("webhook_secret") or "").strip() == secret:
            return account
    return None


def _mock_dispatch_outbound_message(
    *,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
    mark_delivered: bool,
    simulate_failure: bool,
    provider_message_ref: str | None,
    provider_payload: Dict[str, Any] | None,
) -> str | None:
    now = _now_utc()
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if simulate_failure:
        msg.delivery_status = "failed"
        msg.error_message = "Simulated dispatch failure"
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                **(_as_dict(provider_payload) if provider_payload else {}),
            },
        }
        return "simulated_failure"

    msg.delivery_status = "delivered" if mark_delivered else "sent"
    msg.sent_at = msg.sent_at or now
    if mark_delivered:
        msg.delivered_at = msg.delivered_at or now
    msg.error_message = None
    if provider_message_ref and not msg.external_message_ref:
        msg.external_message_ref = provider_message_ref
    if not msg.external_message_ref:
        msg.external_message_ref = f"{thread.channel}:{thread.id}:{msg.id}"
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": msg.delivery_status,
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "thread_channel": thread.channel,
            "channel_account_id": thread.channel_account_id,
            **(_as_dict(provider_payload) if provider_payload else {}),
        },
    }
    return None


def _candidate_name(candidate: Candidate) -> str:
    first = str(getattr(candidate, "first_name", "") or "").strip()
    last = str(getattr(candidate, "last_name", "") or "").strip()
    full = " ".join(x for x in [first, last] if x).strip()
    return full or str(getattr(candidate, "short_id", "") or getattr(candidate, "id", "") or "candidate")


def _candidate_public_status_url(candidate: Candidate) -> str | None:
    token = str(getattr(candidate, "status_share_token", None) or getattr(candidate, "intake_token", None) or "").strip()
    if not token:
        return None
    base_url = str(settings.frontend_url or "https://hostflow.cc").strip() or "https://hostflow.cc"
    return f"{base_url.rstrip('/')}/public/status/{token}"


def _candidate_apply_url(candidate: Candidate) -> str | None:
    token = str(getattr(candidate, "intake_token", None) or "").strip()
    if not token:
        return None
    base_url = str(settings.frontend_url or "https://hostflow.cc").strip() or "https://hostflow.cc"
    return f"{base_url.rstrip('/')}/public/apply/{token}"


def _telegram_extract_command(text: str | None) -> tuple[str, list[str]] | None:
    raw = str(text or "").strip()
    if not raw.startswith("/"):
        return None
    line = raw.splitlines()[0].strip()
    parts = [str(p).strip() for p in line.split(" ") if str(p).strip()]
    if not parts:
        return None
    cmd = parts[0][1:].split("@", 1)[0].strip().lower()
    if not cmd:
        return None
    return cmd, parts[1:]


async def _find_candidate_by_bind_token(
    db: AsyncSession,
    *,
    tenant_id: str,
    token: str,
) -> Candidate | None:
    token_norm = str(token or "").strip()
    if not token_norm:
        return None
    stmt = (
        sa.select(Candidate)
        .where(
            Candidate.tenant_id == tenant_id,
            sa.or_(
                Candidate.intake_token == token_norm,
                Candidate.status_share_token == token_norm,
                Candidate.short_id == token_norm,
                Candidate.id == token_norm,
            ),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


async def _find_candidate_by_telegram_chat(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
) -> Candidate | None:
    chat_ref = str(chat_id or "").strip()
    if not chat_ref:
        return None
    thread_stmt = (
        sa.select(CommunicationThread.linked_candidate_id)
        .where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.channel == "telegram",
            CommunicationThread.channel_thread_ref == chat_ref,
            CommunicationThread.linked_candidate_id.is_not(None),
        )
        .order_by(sa.desc(CommunicationThread.updated_at))
        .limit(1)
    )
    candidate_id = (await db.execute(thread_stmt)).scalar()
    if candidate_id:
        candidate = await db.get(Candidate, str(candidate_id))
        if candidate and str(getattr(candidate, "tenant_id", "")) == tenant_id:
            return candidate
    # Fallback for newly linked chats before thread link sync.
    rows = (
        await db.execute(
            sa.select(Candidate)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.intake_state.is_not(None),
            )
            .limit(5000)
        )
    ).scalars().all()
    for cand in rows:
        state = _as_dict(getattr(cand, "intake_state", None))
        prefs = _as_dict(state.get("notifications"))
        tg = _as_dict(prefs.get("telegram"))
        if str(tg.get("chat_id") or "").strip() == chat_ref:
            return cand
    return None


def _normalize_email_value(value: str | None) -> str | None:
    raw = str(value or "").strip().lower()
    return raw if raw and "@" in raw else None


def _digits_only(value: str | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _looks_like_phone(value: str | None) -> bool:
    d = _digits_only(value)
    return len(d) >= 8


def _is_six_digit_code(value: str | None) -> bool:
    return bool(re.fullmatch(r"\d{6}", str(value or "").strip()))


def _candidate_email_options(candidate: Candidate) -> set[str]:
    opts: set[str] = set()
    email = _normalize_email_value(getattr(candidate, "email", None))
    if email:
        opts.add(email)
    contacts = _as_dict(getattr(candidate, "contacts", None))
    c_email = _normalize_email_value(contacts.get("email"))
    if c_email:
        opts.add(c_email)
    state = _as_dict(getattr(candidate, "intake_state", None))
    intake_contacts = _as_dict(state.get("contacts"))
    s_email = _normalize_email_value(intake_contacts.get("email"))
    if s_email:
        opts.add(s_email)
    return opts


def _candidate_phone_options(candidate: Candidate) -> set[str]:
    opts: set[str] = set()

    def _add(code: Any, phone: Any) -> None:
        p = _digits_only(phone)
        if not p:
            return
        c = _digits_only(code)
        opts.add(p)
        if c:
            opts.add(f"{c}{p}")

    _add(getattr(candidate, "phone_country_code", None), getattr(candidate, "phone", None))
    contacts = _as_dict(getattr(candidate, "contacts", None))
    _add(contacts.get("phone_country_code"), contacts.get("phone"))
    state = _as_dict(getattr(candidate, "intake_state", None))
    intake_contacts = _as_dict(state.get("contacts"))
    _add(intake_contacts.get("phone_country_code"), intake_contacts.get("phone"))
    return opts


async def _find_candidates_by_contact(
    db: AsyncSession,
    *,
    tenant_id: str,
    contact_input: str,
) -> list[Candidate]:
    raw = str(contact_input or "").strip()
    if not raw:
        return []
    email_norm = _normalize_email_value(raw)
    phone_norm = _digits_only(raw)

    rows = (
        await db.execute(
            sa.select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.deleted_at.is_(None),
            ).limit(5000)
        )
    ).scalars().all()
    if not rows:
        return []
    matches: list[Candidate] = []
    seen: set[str] = set()
    for candidate in rows:
        is_match = False
        if email_norm:
            if email_norm in _candidate_email_options(candidate):
                is_match = True
        elif phone_norm:
            for cand_phone in _candidate_phone_options(candidate):
                if cand_phone == phone_norm or cand_phone.endswith(phone_norm) or phone_norm.endswith(cand_phone):
                    is_match = True
                    break
        if is_match and str(candidate.id) not in seen:
            seen.add(str(candidate.id))
            matches.append(candidate)
    return matches


def _telegram_otp_hash(*, chat_id: str, code: str) -> str:
    payload = f"{chat_id}:{code}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _telegram_onboarding_text() -> str:
    base_url = str(settings.frontend_url or "https://hostflow.cc").strip() or "https://hostflow.cc"
    return (
        "Два способа заполнения:\n"
        "1) На сайте: /apply\n"
        "2) Прямо в Telegram: /intake\n\n"
        "Привязка /bind нужна только если профиль уже существует в CRM.\n"
        f"Портал статуса: {base_url.rstrip('/')}/public/portal\n"
        "Если нужна помощь, напишите сообщение менеджеру в этом чате."
    )


def _candidate_verification_email_body(*, candidate_name: str, code: str) -> str:
    return (
        f"Здравствуйте, {candidate_name}!\n\n"
        "Код подтверждения для привязки Telegram к вашей заявке:\n"
        f"{code}\n\n"
        "Код действует 10 минут."
    )


def _telegram_name_parts(sender_label: str | None, username: str | None) -> tuple[str, str]:
    raw = str(sender_label or "").strip()
    if raw and not raw.startswith("@"):
        parts = [p for p in raw.split() if p]
        if len(parts) >= 2:
            return parts[0][:80], " ".join(parts[1:])[:120]
        if len(parts) == 1:
            return parts[0][:80], "Telegram"
    user = str(username or "").strip()
    if user:
        return user[:80], "Telegram"
    return "Telegram", "Candidate"


async def _create_candidate_from_telegram_intake(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
    username: str | None,
    sender_label: str | None,
    sender_address: str | None,
    contact_phone: str | None,
) -> Candidate:
    first_name, last_name = _telegram_name_parts(sender_label, username)
    phone_digits = _digits_only(contact_phone)
    candidate = Candidate(
        id=str(uuid4()),
        tenant_id=tenant_id,
        first_name=first_name,
        last_name=last_name or "Telegram",
        phone=phone_digits or None,
        stage="docs_wait",
        status="docs_wait",
        intake_status="draft",
        source="telegram_bot",
    )
    state = _as_dict(getattr(candidate, "intake_state", None))
    contacts = _as_dict(state.get("contacts"))
    contacts["preferred_messenger"] = "telegram"
    contacts["telegram_chat_id"] = chat_id
    if sender_address:
        contacts["telegram_user_id"] = sender_address
    if username:
        contacts["telegram_username"] = username
    if phone_digits:
        contacts["phone"] = phone_digits
    state["contacts"] = contacts
    candidate.intake_state = state
    _ensure_candidate_intake_token(candidate)
    db.add(candidate)
    await db.flush()
    await _link_candidate_to_telegram_chat(
        db,
        tenant_id=tenant_id,
        chat_id=chat_id,
        candidate=candidate,
        username=username,
    )
    await db.commit()
    return candidate


async def _link_candidate_to_telegram_chat(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
    candidate: Candidate,
    username: str | None,
) -> None:
    now_iso = _now_utc().isoformat()
    state = _as_dict(candidate.intake_state)
    notifications = _as_dict(state.get("notifications"))
    telegram_state = _as_dict(notifications.get("telegram"))
    telegram_state["chat_id"] = chat_id
    telegram_state["subscribed"] = True
    telegram_state["linked_at"] = telegram_state.get("linked_at") or now_iso
    telegram_state["updated_at"] = now_iso
    telegram_state.pop("link_verification", None)
    if username:
        telegram_state["username"] = username
    notifications["telegram"] = telegram_state
    state["notifications"] = notifications
    candidate.intake_state = state

    thread_rows = (
        await db.execute(
            sa.select(CommunicationThread).where(
                CommunicationThread.tenant_id == tenant_id,
                CommunicationThread.channel == "telegram",
                CommunicationThread.channel_thread_ref == chat_id,
            )
        )
    ).scalars().all()
    for thread in thread_rows:
        thread.linked_candidate_id = str(candidate.id)
        if not str(thread.subject or "").strip():
            thread.subject = _candidate_name(candidate)


async def _send_telegram_link_code(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
    username: str | None,
    candidate: Candidate,
    email_to: str,
) -> tuple[bool, str]:
    code = str(secrets.randbelow(900000) + 100000)
    now = _now_utc()
    expires_at = now + timedelta(minutes=10)

    state = _as_dict(candidate.intake_state)
    notifications = _as_dict(state.get("notifications"))
    telegram_state = _as_dict(notifications.get("telegram"))
    telegram_state["chat_id"] = chat_id
    if username:
        telegram_state["username"] = username
    telegram_state["updated_at"] = now.isoformat()
    telegram_state["link_verification"] = {
        "chat_id": chat_id,
        "email": email_to,
        "code_hash": _telegram_otp_hash(chat_id=chat_id, code=code),
        "requested_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "attempts": 0,
    }
    notifications["telegram"] = telegram_state
    state["notifications"] = notifications
    candidate.intake_state = state
    await db.commit()

    candidate_name = _candidate_name(candidate)
    ok = await send_email_for_tenant(
        db,
        tenant_id=tenant_id,
        to=email_to,
        subject="HostFlow: код подтверждения Telegram",
        body=_candidate_verification_email_body(candidate_name=candidate_name, code=code),
    )
    if not ok:
        return False, "Не удалось отправить код на email. Попробуйте позже или напишите менеджеру."
    return True, f"Код подтверждения отправлен на {email_to}. Введите 6 цифр в этом чате."


async def _find_candidate_by_pending_verification(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
) -> Candidate | None:
    rows = (
        await db.execute(
            sa.select(Candidate)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.deleted_at.is_(None),
                Candidate.intake_state.is_not(None),
            )
            .limit(5000)
        )
    ).scalars().all()
    now = _now_utc()
    latest_candidate: Candidate | None = None
    latest_requested_at: datetime | None = None
    for candidate in rows:
        state = _as_dict(candidate.intake_state)
        notifications = _as_dict(state.get("notifications"))
        tg = _as_dict(notifications.get("telegram"))
        pending = _as_dict(tg.get("link_verification"))
        if str(pending.get("chat_id") or "").strip() != chat_id:
            continue
        expires_at = _coerce_datetime(pending.get("expires_at"))
        if expires_at is not None and expires_at < now:
            continue
        requested_at = _coerce_datetime(pending.get("requested_at"))
        if latest_candidate is None or (requested_at and (latest_requested_at is None or requested_at > latest_requested_at)):
            latest_candidate = candidate
            latest_requested_at = requested_at
    return latest_candidate


def _telegram_vacancies_text(vacancies: list[Vacancy]) -> str:
    if not vacancies:
        return "Сейчас нет активных вакансий. Напишите менеджеру, и мы подберем предложение."
    lines = ["Активные вакансии:"]
    for idx, vacancy in enumerate(vacancies[:5], start=1):
        title = str(getattr(vacancy, "title", "") or "Vacancy").strip()
        location = str(getattr(vacancy, "location", "") or "").strip()
        if location:
            lines.append(f"{idx}. {title} ({location})")
        else:
            lines.append(f"{idx}. {title}")
    lines.append("Если интересно, напишите сообщение и менеджер свяжется с вами.")
    return "\n".join(lines)


def _telegram_keyboard(linked: bool) -> Dict[str, Any]:
    if linked:
        rows = [
            [{"text": "/status"}, {"text": "/docs"}],
            [{"text": "/intake"}, {"text": "/apply"}],
            [{"text": "/scan"}, {"text": "/vacancies"}],
            [{"text": "/subscribe"}, {"text": "/unsubscribe"}],
            [{"text": "Связаться с менеджером"}],
        ]
    else:
        rows = [
            [{"text": "/intake"}, {"text": "/apply"}],
            [{"text": "Привязать профиль"}, {"text": "/bind"}],
            [{"text": "Поделиться номером", "request_contact": True}],
            [{"text": "/vacancies"}, {"text": "Связаться с менеджером"}],
        ]
    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


async def _send_candidate_telegram_reply(
    *,
    cfg: TelegramBotConfig,
    chat_id: str,
    text: str,
    linked: bool,
) -> None:
    await send_telegram_text(
        cfg,
        chat_id=chat_id,
        text=text,
        reply_markup=_telegram_keyboard(linked),
    )


def _telegram_help_text() -> str:
    return (
        "Доступные команды:\n"
        "/intake - заполнить анкету в Telegram (создаст профиль, если его еще нет)\n"
        "/apply - заполнить анкету на сайте\n"
        "/bind <token|email|phone> - привязать Telegram к уже существующему профилю\n"
        "/status - текущий этап и статус заявки\n"
        "/intake help - команды анкеты\n"
        "/intake status - показать прогресс анкеты\n"
        "/intake skipped - показать пропущенные опциональные шаги\n"
        "/intake reset - сбросить текущий шаг анкеты и начать с актуального места\n"
        "/intake skip - пропустить текущий шаг (только если шаг опциональный)\n"
        "/intake unskip [step|number] - вернуть пропущенный опциональный шаг в анкету\n"
        "/docs - сводка по документам\n"
        "/scan [doc_type] - открыть сканер документов\n"
        "/subscribe - подписаться на уведомления в Telegram\n"
        "/unsubscribe - отключить уведомления в Telegram\n"
        "/lang <ru|en|pl|uk> - язык уведомлений\n"
        "/vacancies - активные вакансии\n"
        "/help - показать список команд"
    )


def _telegram_docs_summary_text(rows: list[tuple[Any, int]]) -> str:
    if not rows:
        return "По вашему профилю пока нет документов."
    by_status: Dict[str, int] = {}
    total = 0
    for raw_status, cnt in rows:
        if hasattr(raw_status, "value"):
            key = str(getattr(raw_status, "value") or "").strip().lower()
        else:
            key = str(raw_status or "").strip().lower()
        if not key:
            key = "unknown"
        amount = int(cnt or 0)
        by_status[key] = int(by_status.get(key) or 0) + amount
        total += amount
    ordered = [
        "missing",
        "requested",
        "in_progress",
        "submitted",
        "received",
        "approved",
        "completed",
        "rejected",
        "expired",
    ]
    all_keys = ordered + [k for k in by_status.keys() if k not in ordered]
    lines: list[str] = [f"Документы: всего {total}"]
    for key in all_keys:
        if key in by_status:
            lines.append(f"• {key}: {by_status[key]}")
    return "\n".join(lines)


def _json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return {**value}
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _candidate_owner_context_for_docs(candidate: Candidate) -> Dict[str, Any]:
    state = _as_dict(getattr(candidate, "intake_state", None))
    personal_state = _as_dict(state.get("personal"))
    extra_state = _as_dict(state.get("extra"))
    personal_data = _as_dict(getattr(candidate, "personal_data", None))
    extra_data = _json_dict(getattr(candidate, "extra", None))

    raw_docs = extra_state.get("documents")
    if not isinstance(raw_docs, dict):
        raw_docs = extra_data.get("documents")
    docs_ctx = {
        str(key): bool(value)
        for key, value in (raw_docs.items() if isinstance(raw_docs, dict) else [])
        if isinstance(value, bool)
    }

    has_adr = personal_state.get("has_adr")
    if has_adr is None:
        has_adr = extra_state.get("has_adr")
    if has_adr is None:
        has_adr = extra_data.get("has_adr")

    ctx: Dict[str, Any] = {
        "candidate_id": str(getattr(candidate, "id", "") or "").strip() or None,
        "citizenship": (
            personal_state.get("citizenship")
            or personal_data.get("citizenship")
            or extra_data.get("citizenship")
        ),
        "residency_status": (
            extra_state.get("poland_stay_basis")
            or extra_data.get("poland_stay_basis")
            or personal_state.get("residency_status")
            or personal_data.get("residency_status")
        ),
        "has_adr": has_adr if isinstance(has_adr, bool) else None,
        "documents": docs_ctx,
    }
    return {k: v for k, v in ctx.items() if v is not None}


def _format_doc_types_bullets(items: list[str], *, limit: int = 5) -> list[str]:
    if not items:
        return []
    labels = [str(get_document_display_name(code) or code) for code in items]
    lines = [f"• {label}" for label in labels[:limit]]
    remaining = len(labels) - limit
    if remaining > 0:
        lines.append(f"• +{remaining} еще")
    return lines


_TG_INTL_BOOL_TRUE = {"yes", "y", "true", "1", "да", "д", "есть", "ok", "ага"}
_TG_INTL_BOOL_FALSE = {"no", "n", "false", "0", "нет", "н", "не", "none"}
_TG_INTAKE_STEP_ORDER: list[str] = [
    "full_name",
    "birth_date",
    "citizenship",
    "years_ce",
    "intl_experience",
    "has_adr",
    "agreement_general",
]
_TG_INTAKE_OPTIONAL_STEPS: set[str] = {
    "intl_experience",
    "has_adr",
}


def _tg_answer_yes_no(value: str) -> bool | None:
    normalized = str(value or "").strip().lower()
    if normalized in _TG_INTL_BOOL_TRUE:
        return True
    if normalized in _TG_INTL_BOOL_FALSE:
        return False
    return None


def _tg_get_intake_sections(candidate: Candidate) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    state = _as_dict(getattr(candidate, "intake_state", None))
    contacts = _as_dict(state.get("contacts"))
    personal = _as_dict(state.get("personal"))
    experience = _as_dict(state.get("experience"))
    agreements = _as_dict(state.get("agreements"))
    runtime = _as_dict(state.get("telegram_intake"))
    return contacts, personal, experience, agreements, runtime


def _tg_incomplete_steps(candidate: Candidate) -> list[str]:
    _, personal, experience, agreements, runtime = _tg_get_intake_sections(candidate)
    skipped_steps_raw = runtime.get("skipped_steps")
    skipped_steps = {
        str(item).strip()
        for item in (skipped_steps_raw if isinstance(skipped_steps_raw, list) else [])
        if str(item).strip()
    }
    name_ready = bool(str(getattr(candidate, "first_name", "") or "").strip() and str(getattr(candidate, "last_name", "") or "").strip())
    if not name_ready:
        full_name_state = str(personal.get("full_name") or "").strip()
        name_ready = bool(full_name_state and len(full_name_state.split()) >= 2)
    checks: Dict[str, bool] = {
        "full_name": name_ready,
        "birth_date": bool(str(personal.get("birth_date") or "").strip()),
        "citizenship": len(str(personal.get("citizenship") or "").strip()) == 2,
        "years_ce": isinstance(experience.get("years_ce"), int),
        "intl_experience": isinstance(experience.get("intl_experience"), bool),
        "has_adr": isinstance(personal.get("has_adr"), bool),
        "agreement_general": bool(agreements.get("general") is True),
    }
    return [
        step
        for step in _TG_INTAKE_STEP_ORDER
        if not checks.get(step) and not (step in _TG_INTAKE_OPTIONAL_STEPS and step in skipped_steps)
    ]


def _tg_step_prompt(step: str, *, index: int, total: int) -> str:
    prefix = f"Анкета {index}/{total}\n"
    prompts: Dict[str, str] = {
        "full_name": "Введите имя и фамилию (например: Jan Kowalski).",
        "birth_date": "Дата рождения: YYYY-MM-DD (например 1990-05-17).",
        "citizenship": "Гражданство: 2 буквы кода страны (например PL, UA, BY).",
        "years_ce": "Сколько лет опыта по категории CE? (целое число от 0 до 40).",
        "intl_experience": "Есть международный опыт перевозок? Ответьте: да/нет.",
        "has_adr": "Есть ADR? Ответьте: да/нет.",
        "agreement_general": "Подтверждаете согласие на обработку данных? Ответьте: да/нет.",
    }
    return f"{prefix}{prompts.get(step) or 'Введите ответ.'}"


def _tg_step_label(step: str) -> str:
    labels: Dict[str, str] = {
        "full_name": "Имя и фамилия",
        "birth_date": "Дата рождения",
        "citizenship": "Гражданство",
        "years_ce": "Опыт CE (лет)",
        "intl_experience": "Международный опыт",
        "has_adr": "Наличие ADR",
        "agreement_general": "Согласие на обработку данных",
    }
    return labels.get(step) or step


def _tg_intake_progress_text(candidate: Candidate) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    skipped = {
        str(item).strip()
        for item in (runtime.get("skipped_steps") if isinstance(runtime.get("skipped_steps"), list) else [])
        if str(item).strip()
    }
    missing = _tg_incomplete_steps(candidate)
    total = len(_TG_INTAKE_STEP_ORDER)
    done = max(0, total - len(missing))
    if not missing:
        return "Анкета заполнена: 7/7. Следующий шаг: /docs и /scan."
    current = str(runtime.get("current_step") or "").strip()
    if current not in missing:
        current = missing[0]
    lines = [
        f"Прогресс анкеты: {done}/{total}",
        f"Текущий шаг: {_tg_step_label(current)}",
        "Осталось:",
    ]
    for step in missing[:4]:
        lines.append(f"• {_tg_step_label(step)}")
    if len(missing) > 4:
        lines.append(f"• +{len(missing) - 4} еще")
    if skipped:
        lines.append(f"Пропущено опционально: {len(skipped)}")
        ordered_skipped = [step for step in _TG_INTAKE_STEP_ORDER if step in skipped]
        if ordered_skipped:
            lines.append("Можно вернуть командой:")
            for idx, step in enumerate(ordered_skipped, start=1):
                lines.append(f"• /intake unskip {idx} ({_tg_step_label(step)}; key: {step})")
            lines.append("Или вернуть последний пропущенный: /intake unskip")
    lines.append("Продолжить: /intake")
    return "\n".join(lines)


def _tg_intake_skipped_text(candidate: Candidate) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    skipped = {
        str(item).strip()
        for item in (runtime.get("skipped_steps") if isinstance(runtime.get("skipped_steps"), list) else [])
        if str(item).strip()
    }
    ordered_skipped = [step for step in _TG_INTAKE_STEP_ORDER if step in skipped]
    if not ordered_skipped:
        return "Пропущенных опциональных шагов нет."
    lines = [
        f"Пропущенные опциональные шаги: {len(ordered_skipped)}",
        "Вернуть можно командами:",
    ]
    for idx, step in enumerate(ordered_skipped, start=1):
        lines.append(f"• /intake unskip {idx} ({_tg_step_label(step)}; key: {step})")
    lines.append("Или вернуть последний: /intake unskip")
    return "\n".join(lines)


def _tg_intake_help_text() -> str:
    return (
        "Команды анкеты:\n"
        "/intake - начать или продолжить анкету\n"
        "/intake status - прогресс и текущий шаг\n"
        "/intake skipped - список пропущенных опциональных шагов\n"
        "/intake skip - пропустить текущий шаг (если он опциональный)\n"
        "/intake unskip [step|number] - вернуть пропущенный шаг\n"
        "/intake reset - сбросить runtime-курсор к первому незаполненному шагу\n"
        "/intake help - показать эту подсказку"
    )


async def _tg_reset_intake_runtime(
    db: AsyncSession,
    *,
    candidate: Candidate,
    chat_id: str,
    username: str | None,
) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    missing = _tg_incomplete_steps(candidate)
    runtime["chat_id"] = chat_id
    if username:
        runtime["username"] = username
    runtime["active"] = bool(missing)
    runtime["current_step"] = missing[0] if missing else None
    runtime["updated_at"] = _now_utc().isoformat()
    state["telegram_intake"] = runtime
    candidate.intake_state = state
    await db.commit()
    if not missing:
        return "Анкета уже заполнена. Нечего сбрасывать."
    idx = _TG_INTAKE_STEP_ORDER.index(missing[0]) + 1 if missing[0] in _TG_INTAKE_STEP_ORDER else 1
    return (
        "Текущий шаг анкеты сброшен. Ответы сохранены.\n\n"
        + _tg_step_prompt(missing[0], index=idx, total=len(_TG_INTAKE_STEP_ORDER))
    )


async def _tg_skip_intake_step(
    db: AsyncSession,
    *,
    candidate: Candidate,
    chat_id: str,
    username: str | None,
) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    missing = _tg_incomplete_steps(candidate)
    if not missing:
        runtime["active"] = False
        runtime["current_step"] = None
        runtime["completed_at"] = _now_utc().isoformat()
        runtime["updated_at"] = _now_utc().isoformat()
        state["telegram_intake"] = runtime
        candidate.intake_state = state
        await db.commit()
        return "Анкета уже заполнена. Пропуск не требуется."

    current = str(runtime.get("current_step") or "").strip()
    if current not in missing:
        current = missing[0]
    if current not in _TG_INTAKE_OPTIONAL_STEPS:
        idx = _TG_INTAKE_STEP_ORDER.index(current) + 1 if current in _TG_INTAKE_STEP_ORDER else 1
        return (
            f"Шаг «{_tg_step_label(current)}» обязательный и не может быть пропущен.\n\n"
            f"{_tg_step_prompt(current, index=idx, total=len(_TG_INTAKE_STEP_ORDER))}"
        )

    skipped_raw = runtime.get("skipped_steps")
    skipped = [str(item).strip() for item in (skipped_raw if isinstance(skipped_raw, list) else []) if str(item).strip()]
    if current not in skipped:
        skipped.append(current)
    runtime["skipped_steps"] = skipped
    runtime["chat_id"] = chat_id
    if username:
        runtime["username"] = username
    runtime["updated_at"] = _now_utc().isoformat()

    state["telegram_intake"] = runtime
    candidate.intake_state = state

    remaining = _tg_incomplete_steps(candidate)
    if not remaining:
        runtime["active"] = False
        runtime["current_step"] = None
        runtime["completed_at"] = _now_utc().isoformat()
        runtime["updated_at"] = _now_utc().isoformat()
        state["telegram_intake"] = runtime
        candidate.intake_state = state
        await db.commit()
        return (
            f"Шаг «{_tg_step_label(current)}» пропущен.\n"
            "Анкета заполнена. Следующий шаг: /docs и /scan."
        )

    next_step = remaining[0]
    runtime["active"] = True
    runtime["current_step"] = next_step
    runtime["updated_at"] = _now_utc().isoformat()
    state["telegram_intake"] = runtime
    candidate.intake_state = state
    await db.commit()
    idx = _TG_INTAKE_STEP_ORDER.index(next_step) + 1 if next_step in _TG_INTAKE_STEP_ORDER else 1
    return (
        f"Шаг «{_tg_step_label(current)}» пропущен (опционально).\n\n"
        + _tg_step_prompt(next_step, index=idx, total=len(_TG_INTAKE_STEP_ORDER))
    )


async def _tg_unskip_intake_step(
    db: AsyncSession,
    *,
    candidate: Candidate,
    chat_id: str,
    username: str | None,
    target_step: str | None = None,
) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    skipped_raw = runtime.get("skipped_steps")
    skipped = [str(item).strip() for item in (skipped_raw if isinstance(skipped_raw, list) else []) if str(item).strip()]
    if not skipped:
        return "Нет пропущенных опциональных шагов."

    ordered_skipped = [step for step in _TG_INTAKE_STEP_ORDER if step in skipped]
    target = str(target_step or "").strip().lower()
    if target and re.fullmatch(r"\d+", target):
        numeric = int(target)
        if numeric < 1 or numeric > len(ordered_skipped):
            return f"Неверный номер шага. Укажите 1..{len(ordered_skipped)}."
        target = ordered_skipped[numeric - 1]
    if target:
        if target not in _TG_INTAKE_OPTIONAL_STEPS:
            allowed = ", ".join(sorted(_TG_INTAKE_OPTIONAL_STEPS))
            return f"Можно вернуть только опциональные шаги: {allowed}."
        if target not in skipped:
            listed = ", ".join(skipped)
            return f"Шаг `{target}` не найден среди пропущенных. Сейчас пропущено: {listed}."
        step_to_restore = target
    else:
        step_to_restore = skipped[-1]

    skipped = [step for step in skipped if step != step_to_restore]
    runtime["skipped_steps"] = skipped
    runtime["active"] = True
    runtime["current_step"] = step_to_restore
    runtime["chat_id"] = chat_id
    if username:
        runtime["username"] = username
    runtime["updated_at"] = _now_utc().isoformat()

    state["telegram_intake"] = runtime
    candidate.intake_state = state
    await db.commit()

    idx = _TG_INTAKE_STEP_ORDER.index(step_to_restore) + 1 if step_to_restore in _TG_INTAKE_STEP_ORDER else 1
    return (
        f"Шаг «{_tg_step_label(step_to_restore)}» возвращен в анкету.\n\n"
        + _tg_step_prompt(step_to_restore, index=idx, total=len(_TG_INTAKE_STEP_ORDER))
    )


def _tg_parse_step_answer(step: str, text: str) -> tuple[bool, Any, str | None]:
    raw = str(text or "").strip()
    if not raw:
        return False, None, "Ответ пустой. Попробуйте еще раз."
    if step == "full_name":
        parts = [p for p in raw.split() if p]
        if len(parts) < 2:
            return False, None, "Нужно указать имя и фамилию."
        first = parts[0].strip()
        last = " ".join(parts[1:]).strip()
        if len(first) < 2 or len(last) < 2:
            return False, None, "Имя/фамилия слишком короткие."
        return True, {"first_name": first, "last_name": last, "full_name": f"{first} {last}"}, None
    if step == "birth_date":
        normalized = raw.replace("/", "-").replace(".", "-")
        try:
            if len(normalized) == 10 and normalized[4] == "-":
                parsed = datetime.strptime(normalized, "%Y-%m-%d")
            else:
                parsed = datetime.strptime(normalized, "%d-%m-%Y")
            return True, parsed.date().isoformat(), None
        except Exception:
            return False, None, "Неверный формат даты. Используйте YYYY-MM-DD."
    if step == "citizenship":
        code = re.sub(r"[^A-Za-z]", "", raw).upper()
        if len(code) != 2:
            return False, None, "Укажите код из 2 букв (например PL)."
        return True, code, None
    if step == "years_ce":
        try:
            years = int(raw)
        except Exception:
            return False, None, "Нужно целое число, например 3."
        if years < 0 or years > 40:
            return False, None, "Допустимый диапазон: 0..40."
        return True, years, None
    if step in {"intl_experience", "has_adr", "agreement_general"}:
        value = _tg_answer_yes_no(raw)
        if value is None:
            return False, None, "Ответьте «да» или «нет»."
        return True, value, None
    return True, raw, None


def _tg_apply_step_answer(candidate: Candidate, step: str, value: Any) -> None:
    state = _as_dict(getattr(candidate, "intake_state", None))
    state["contacts"] = _as_dict(state.get("contacts"))
    state["personal"] = _as_dict(state.get("personal"))
    state["experience"] = _as_dict(state.get("experience"))
    state["agreements"] = _as_dict(state.get("agreements"))

    if step == "full_name":
        first_name = str(_as_dict(value).get("first_name") or "").strip()
        last_name = str(_as_dict(value).get("last_name") or "").strip()
        if first_name:
            candidate.first_name = first_name
        if last_name:
            candidate.last_name = last_name
        state["personal"]["full_name"] = str(_as_dict(value).get("full_name") or "").strip()
    elif step == "birth_date":
        state["personal"]["birth_date"] = str(value or "").strip()
        pd = _as_dict(getattr(candidate, "personal_data", None))
        pd["birth_date"] = str(value or "").strip()
        candidate.personal_data = pd
        extra = _json_dict(getattr(candidate, "extra", None))
        extra["birth_date"] = str(value or "").strip()
        candidate._set_extra(extra)
    elif step == "citizenship":
        state["personal"]["citizenship"] = str(value or "").upper()
        pd = _as_dict(getattr(candidate, "personal_data", None))
        pd["citizenship"] = str(value or "").upper()
        candidate.personal_data = pd
        extra = _json_dict(getattr(candidate, "extra", None))
        extra["citizenship"] = str(value or "").upper()
        candidate._set_extra(extra)
    elif step == "years_ce":
        state["experience"]["years_ce"] = int(value)
        extra = _json_dict(getattr(candidate, "extra", None))
        extra["experience_eu_years"] = int(value)
        candidate._set_extra(extra)
    elif step == "intl_experience":
        state["experience"]["intl_experience"] = bool(value)
        extra = _json_dict(getattr(candidate, "extra", None))
        extra["intl_experience"] = bool(value)
        candidate._set_extra(extra)
    elif step == "has_adr":
        state["personal"]["has_adr"] = bool(value)
        pd = _as_dict(getattr(candidate, "personal_data", None))
        pd["has_adr"] = bool(value)
        candidate.personal_data = pd
        extra = _json_dict(getattr(candidate, "extra", None))
        extra["has_adr"] = bool(value)
        candidate._set_extra(extra)
    elif step == "agreement_general":
        state["agreements"]["general"] = bool(value)
        if bool(value):
            state["agreements"]["general_accepted_at"] = _now_utc().isoformat()

    runtime = _as_dict(state.get("telegram_intake"))
    runtime.setdefault("completed_steps", [])
    completed = runtime.get("completed_steps")
    if not isinstance(completed, list):
        completed = []
    if step not in completed:
        completed.append(step)
    runtime["completed_steps"] = completed
    runtime["updated_at"] = _now_utc().isoformat()
    state["telegram_intake"] = runtime
    candidate.intake_state = state


async def _tg_start_or_resume_intake(db: AsyncSession, *, candidate: Candidate, chat_id: str, username: str | None) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    missing = _tg_incomplete_steps(candidate)
    if not missing:
        runtime["active"] = False
        runtime["current_step"] = None
        runtime["completed_at"] = _now_utc().isoformat()
        runtime["updated_at"] = _now_utc().isoformat()
        state["telegram_intake"] = runtime
        candidate.intake_state = state
        await db.commit()
        return "Анкета уже заполнена. Проверьте /docs или отправьте /apply для ссылки на анкету."
    current = str(runtime.get("current_step") or "").strip()
    if current not in missing:
        current = missing[0]
    runtime["active"] = True
    runtime["current_step"] = current
    runtime["chat_id"] = chat_id
    if username:
        runtime["username"] = username
    runtime["updated_at"] = _now_utc().isoformat()
    state["telegram_intake"] = runtime
    candidate.intake_state = state
    await db.commit()
    idx = _TG_INTAKE_STEP_ORDER.index(current) + 1 if current in _TG_INTAKE_STEP_ORDER else 1
    return _tg_step_prompt(current, index=idx, total=len(_TG_INTAKE_STEP_ORDER))


async def _tg_process_intake_answer(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    text: str,
) -> str | None:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    if not bool(runtime.get("active")):
        return None
    current = str(runtime.get("current_step") or "").strip()
    missing = _tg_incomplete_steps(candidate)
    if current not in missing:
        if not missing:
            runtime["active"] = False
            runtime["current_step"] = None
            runtime["completed_at"] = _now_utc().isoformat()
            runtime["updated_at"] = _now_utc().isoformat()
            state["telegram_intake"] = runtime
            candidate.intake_state = state
            await db.commit()
            return await _tg_intake_completion_docs_text(
                db,
                tenant_id=tenant_id,
                candidate=candidate,
            )
        current = missing[0]
        runtime["current_step"] = current
        state["telegram_intake"] = runtime
        candidate.intake_state = state
        await db.commit()
    ok, parsed_value, error = _tg_parse_step_answer(current, text)
    if not ok:
        idx = _TG_INTAKE_STEP_ORDER.index(current) + 1 if current in _TG_INTAKE_STEP_ORDER else 1
        return f"{error}\n\n{_tg_step_prompt(current, index=idx, total=len(_TG_INTAKE_STEP_ORDER))}"

    _tg_apply_step_answer(candidate, current, parsed_value)
    candidate.intake_status = str(getattr(candidate, "intake_status", "") or "draft")
    remaining = _tg_incomplete_steps(candidate)
    runtime = _as_dict(_as_dict(getattr(candidate, "intake_state", None)).get("telegram_intake"))
    if not remaining:
        runtime["active"] = False
        runtime["current_step"] = None
        runtime["completed_at"] = _now_utc().isoformat()
        runtime.setdefault("ready_for_docs_notified_at", _now_utc().isoformat())
        runtime["updated_at"] = _now_utc().isoformat()
        _ensure_candidate_intake_token(candidate)
        state = _as_dict(getattr(candidate, "intake_state", None))
        state["telegram_intake"] = runtime
        candidate.intake_state = state
        if not str(runtime.get("ready_for_docs_event_logged_at") or "").strip():
            try:
                await log_activity(
                    db,
                    tenant_id=str(tenant_id or "").strip(),
                    action="candidate_ready_for_docs",
                    actor_id=None,
                    target_type="candidate",
                    target_id=str(getattr(candidate, "id", "") or "").strip() or None,
                    payload={
                        "source": "telegram_intake",
                        "channel": "telegram",
                        "completed_at": str(runtime.get("completed_at") or ""),
                        "intake_status": str(getattr(candidate, "intake_status", "") or ""),
                    },
                )
            except Exception:
                logger.exception(
                    "telegram intake ready_for_docs audit failed tenant=%s candidate=%s",
                    tenant_id,
                    getattr(candidate, "id", None),
                )
            runtime["ready_for_docs_event_logged_at"] = _now_utc().isoformat()
            state["telegram_intake"] = runtime
            candidate.intake_state = state
        try:
            await sync_candidate_ready_for_handoff_gate(
                db,
                tenant_id=tenant_id,
                candidate=candidate,
                source="telegram_intake_completion",
            )
        except Exception:
            logger.exception(
                "telegram intake auto-ready-for-handoff sync failed tenant=%s candidate=%s",
                tenant_id,
                getattr(candidate, "id", None),
            )
        await db.commit()
        return await _tg_intake_completion_docs_text(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
        )

    next_step = remaining[0]
    runtime["active"] = True
    runtime["current_step"] = next_step
    runtime["updated_at"] = _now_utc().isoformat()
    state = _as_dict(getattr(candidate, "intake_state", None))
    state["telegram_intake"] = runtime
    candidate.intake_state = state
    await db.commit()
    idx = _TG_INTAKE_STEP_ORDER.index(next_step) + 1 if next_step in _TG_INTAKE_STEP_ORDER else 1
    return _tg_step_prompt(next_step, index=idx, total=len(_TG_INTAKE_STEP_ORDER))


async def _telegram_docs_checklist_text(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> str:
    snapshot = await _telegram_required_docs_snapshot(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
    )
    total = int(snapshot.get("total") or 0)
    ready = int(snapshot.get("ready") or 0)
    in_progress = list(snapshot.get("in_progress") or [])
    missing = list(snapshot.get("missing") or [])
    problematic = list(snapshot.get("problematic") or [])
    docs_count = int(snapshot.get("docs_count") or 0)

    if total <= 0:
        if docs_count > 0:
            return f"Документы загружены: {docs_count}. Обязательный чеклист не задан."
        return "По вашему профилю пока нет документов и обязательного чеклиста."

    lines: list[str] = [f"Чеклист документов: {ready}/{total} готово"]
    if missing:
        lines.append("Не хватает:")
        lines.extend(_format_doc_types_bullets(missing))
    if in_progress:
        lines.append("В обработке:")
        lines.extend(_format_doc_types_bullets(in_progress))
    if problematic:
        lines.append("Нужна замена/исправление:")
        lines.extend(_format_doc_types_bullets(problematic))
    return "\n".join(lines)


async def _tg_intake_completion_docs_text(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> str:
    lines: list[str] = [
        "Анкета заполнена. Спасибо.",
    ]
    try:
        snapshot = await _telegram_required_docs_snapshot(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
        )
        total = int(snapshot.get("total") or 0)
        ready = int(snapshot.get("ready") or 0)
        missing = [str(x) for x in (snapshot.get("missing") or []) if str(x or "").strip()]
        in_progress = [str(x) for x in (snapshot.get("in_progress") or []) if str(x or "").strip()]
        problematic = [str(x) for x in (snapshot.get("problematic") or []) if str(x or "").strip()]

        if total > 0:
            lines.append(f"Чеклист документов: {ready}/{total} готово")
            if missing:
                lines.append("Осталось загрузить:")
                lines.extend(_format_doc_types_bullets(missing, limit=3))
        else:
            docs_count = int(snapshot.get("docs_count") or 0)
            if docs_count > 0:
                lines.append(f"Документы уже загружены: {docs_count}.")
            else:
                lines.append("Обязательный чеклист пока не настроен. Можете открыть /docs.")

        next_doc = missing[0] if missing else (in_progress[0] if in_progress else (problematic[0] if problematic else None))
        scan_url = _candidate_scan_url(candidate, doc_type=next_doc)
        if next_doc:
            lines.append(f"Следующий шаг: /scan {next_doc}")
        if scan_url:
            lines.append(f"Ссылка на сканер: {scan_url}")
        lines.append("Полный список документов: /docs")
    except Exception:
        logger.exception(
            "telegram intake completion docs-summary failed tenant=%s candidate=%s",
            tenant_id,
            getattr(candidate, "id", None),
        )
        lines.append("Дальше проверьте список обязательных документов командой /docs.")
    return "\n".join(lines)


def _generate_public_candidate_token() -> str:
    return secrets.token_urlsafe(24)


def _ensure_candidate_intake_token(candidate: Candidate) -> bool:
    now = _now_utc()
    token = str(getattr(candidate, "intake_token", None) or "").strip()
    expires_at = _coerce_datetime(getattr(candidate, "intake_token_expires_at", None))
    if token and expires_at and expires_at > now:
        return False
    if not token:
        candidate.intake_token = _generate_public_candidate_token()
        candidate.intake_token_created_at = now
    candidate.intake_token_expires_at = now + timedelta(days=30)
    return True


def _candidate_scan_url(candidate: Candidate, doc_type: str | None = None) -> str | None:
    token = str(getattr(candidate, "intake_token", None) or "").strip()
    if not token:
        return None
    base_url = str(settings.frontend_url or "https://hostflow.cc").strip() or "https://hostflow.cc"
    params: Dict[str, str] = {"token": token}
    doc_norm = str(doc_type or "").strip()
    if doc_norm:
        params["doc"] = doc_norm
    return f"{base_url.rstrip('/')}/public/scan?{urlencode(params)}"


async def _telegram_required_docs_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Dict[str, Any]:
    ruleset_version = await ensure_ruleset_seed(
        db,
        str(tenant_id),
        load_default_ruleset(),
    )
    ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
    owner_context = _candidate_owner_context_for_docs(candidate)

    doc_rows = (
        await db.execute(
            sa.select(Document.doc_type, Document.status, Document.expire_date)
            .where(
                Document.tenant_id == str(tenant_id),
                Document.candidate_id == str(candidate.id),
                Document.deleted_at.is_(None),
            )
        )
    ).all()

    serialized_docs: list[dict[str, Any]] = []
    for doc_type, status, expire_date in doc_rows:
        status_value = status.value if hasattr(status, "value") else str(status or "").strip().lower()
        serialized_docs.append(
            {
                "type": str(doc_type or "").strip(),
                "doc_type": str(doc_type or "").strip(),
                "status": status_value,
                "expires_at": expire_date.isoformat() if expire_date is not None else None,
            }
        )

    summary = compute_owner_summary(owner_context, ruleset_payload, serialized_docs)
    required = _as_dict(summary.get("required"))
    return {
        "total": int(required.get("total") or 0),
        "ready": int(required.get("ready") or 0),
        "in_progress": [str(item) for item in (required.get("in_progress_types") or []) if str(item or "").strip()],
        "missing": [str(item) for item in (required.get("missing") or []) if str(item or "").strip()],
        "problematic": [str(item) for item in (required.get("problematic") or []) if str(item or "").strip()],
        "docs_count": len(serialized_docs),
    }


async def _telegram_scan_command_text(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    requested_doc_type: str | None = None,
) -> str:
    snapshot = await _telegram_required_docs_snapshot(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
    )
    missing = list(snapshot.get("missing") or [])
    in_progress = list(snapshot.get("in_progress") or [])
    problematic = list(snapshot.get("problematic") or [])

    requested = str(requested_doc_type or "").strip().lower()
    if requested:
        requested = re.sub(r"[^a-z0-9_]", "", requested)
    preferred_doc: str | None = None
    allowed_docs = set(missing + in_progress + problematic)
    if requested and requested in allowed_docs:
        preferred_doc = requested
    elif missing:
        preferred_doc = missing[0]
    elif in_progress:
        preferred_doc = in_progress[0]
    elif problematic:
        preferred_doc = problematic[0]
    elif requested:
        preferred_doc = requested

    scan_url = _candidate_scan_url(candidate, preferred_doc)
    apply_url = _candidate_apply_url(candidate)
    if not scan_url:
        if apply_url:
            return f"Сканер недоступен без intake token. Откройте анкету: {apply_url}"
        return "Сканер пока недоступен. Обратитесь к менеджеру."

    lines: list[str] = []
    if preferred_doc:
        label = str(get_document_display_name(preferred_doc) or preferred_doc)
        lines.append(f"Сканер для документа «{label}»:")
    else:
        lines.append("Откройте сканер документов:")
    lines.append(scan_url)
    if missing:
        lines.append("")
        lines.append("Осталось загрузить обязательно:")
        lines.extend(_format_doc_types_bullets(missing, limit=3))
    if apply_url:
        lines.append("")
        lines.append(f"Полная анкета: {apply_url}")
    return "\n".join(lines)


async def _process_public_telegram_candidate_command(
    db: AsyncSession,
    *,
    account: CommunicationChannelAccount,
    tenant_id: str,
    normalized: Dict[str, Any],
) -> tuple[bool, str | None]:
    text = normalized.get("text")
    text_str = str(text or "").strip() if isinstance(text, str) else ""
    parsed = _telegram_extract_command(text_str)
    cmd = ""
    args: list[str] = []
    if parsed:
        cmd, args = parsed

    chat_id = str(normalized.get("provider_chat_ref") or "").strip()
    if not chat_id:
        return False, None
    cfg = _telegram_config_from_account_settings(account)
    if cfg is None:
        return False, None

    payload_data = _as_dict(normalized.get("payload"))
    username = str(payload_data.get("telegram_username") or "").strip() or None
    sender_label = str(normalized.get("sender_label") or "").strip() or None
    sender_address = str(normalized.get("sender_address") or "").strip() or None
    contact_phone = str(payload_data.get("telegram_contact_phone") or "").strip() or None
    now_iso = _now_utc().isoformat()
    reply = ""
    linked_candidate_id: str | None = None

    linked_candidate = await _find_candidate_by_telegram_chat(db, tenant_id=tenant_id, chat_id=chat_id)
    if linked_candidate is not None:
        linked_candidate_id = str(linked_candidate.id)

    # Non-command input: support OTP and contact-based linking.
    if not parsed:
        if linked_candidate is not None:
            intake_reply = await _tg_process_intake_answer(
                db,
                tenant_id=tenant_id,
                candidate=linked_candidate,
                text=text_str,
            )
            if intake_reply:
                reply = intake_reply
                linked_candidate_id = str(linked_candidate.id)

        if text_str.lower() in {"связаться с менеджером", "manager", "contact manager"}:
            if linked_candidate is not None:
                reply = "Сообщение передано менеджеру. Ответ придет в этот чат."
                linked_candidate_id = str(linked_candidate.id)
            else:
                reply = "Напишите коротко ваш вопрос. Менеджер подключится к диалогу."
        
        if linked_candidate is None and not reply:
            if _is_six_digit_code(text_str):
                pending_candidate = await _find_candidate_by_pending_verification(db, tenant_id=tenant_id, chat_id=chat_id)
                if pending_candidate is not None:
                    state = _as_dict(pending_candidate.intake_state)
                    notifications = _as_dict(state.get("notifications"))
                    tg = _as_dict(notifications.get("telegram"))
                    pending = _as_dict(tg.get("link_verification"))
                    expires_at = _coerce_datetime(pending.get("expires_at"))
                    if expires_at is not None and expires_at < _now_utc():
                        tg.pop("link_verification", None)
                        notifications["telegram"] = tg
                        state["notifications"] = notifications
                        pending_candidate.intake_state = state
                        await db.commit()
                        reply = "Код истек. Отправьте email или телефон повторно, чтобы получить новый код."
                    else:
                        attempts = int(pending.get("attempts") or 0)
                        if attempts >= 5:
                            tg.pop("link_verification", None)
                            notifications["telegram"] = tg
                            state["notifications"] = notifications
                            pending_candidate.intake_state = state
                            await db.commit()
                            reply = "Слишком много попыток. Запросите новый код по email или телефону."
                        else:
                            expected_hash = str(pending.get("code_hash") or "")
                            if expected_hash and expected_hash == _telegram_otp_hash(chat_id=chat_id, code=text_str):
                                await _link_candidate_to_telegram_chat(
                                    db,
                                    tenant_id=tenant_id,
                                    chat_id=chat_id,
                                    candidate=pending_candidate,
                                    username=username,
                                )
                                await db.commit()
                                linked_candidate_id = str(pending_candidate.id)
                                reply = (
                                    f"Готово. Профиль {_candidate_name(pending_candidate)} привязан.\n"
                                    "Теперь доступны /status, /docs и /subscribe."
                                )
                            else:
                                pending["attempts"] = attempts + 1
                                tg["link_verification"] = pending
                                notifications["telegram"] = tg
                                state["notifications"] = notifications
                                pending_candidate.intake_state = state
                                await db.commit()
                                reply = "Неверный код. Проверьте email и попробуйте снова."
                else:
                    reply = "Сначала отправьте email или номер телефона, чтобы получить код."
            elif _normalize_email_value(text_str) or _looks_like_phone(text_str):
                matches = await _find_candidates_by_contact(db, tenant_id=tenant_id, contact_input=text_str)
                if not matches:
                    reply = _telegram_onboarding_text()
                elif len(matches) > 1:
                    reply = (
                        "Найдено несколько кандидатов. Для точной привязки отправьте email, "
                        "который указан в анкете."
                    )
                else:
                    candidate = matches[0]
                    email_opts = sorted(_candidate_email_options(candidate))
                    email_to = email_opts[0] if email_opts else None
                    if not email_to:
                        reply = (
                            "Для этого профиля не найден email. Напишите менеджеру в этот чат, "
                            "мы поможем с привязкой."
                        )
                    else:
                        ok, msg = await _send_telegram_link_code(
                            db,
                            tenant_id=tenant_id,
                            chat_id=chat_id,
                            username=username,
                            candidate=candidate,
                            email_to=email_to,
                        )
                        reply = msg
            else:
                if text_str.lower() in {"привязать профиль", "bind", "link"}:
                    reply = "Отправьте email или номер телефона, который вы указывали в анкете."
                else:
                    reply = _telegram_onboarding_text()

        if reply:
            try:
                await _send_candidate_telegram_reply(
                    cfg=cfg,
                    chat_id=chat_id,
                    text=reply,
                    linked=bool(linked_candidate_id),
                )
            except Exception:
                logger.exception(
                    "communications telegram command reply failed tenant=%s account=%s command=%s",
                    tenant_id,
                    account.id,
                    "non_command",
                )
            return True, linked_candidate_id
        return False, linked_candidate_id

    if cmd not in {"start", "help", "bind", "status", "intake", "docs", "scan", "subscribe", "unsubscribe", "lang", "vacancies", "apply"}:
        return False, linked_candidate_id

    if cmd in {"start", "help"}:
        reply = f"{_telegram_onboarding_text()}\n\n{_telegram_help_text()}"
    elif cmd == "bind":
        bind_value = str(args[0] if args else "").strip()
        if not bind_value:
            reply = "Отправьте `/bind <email или телефон>` или просто напишите email/телефон в чат."
        else:
            if _normalize_email_value(bind_value) or _looks_like_phone(bind_value):
                matches = await _find_candidates_by_contact(db, tenant_id=tenant_id, contact_input=bind_value)
                if not matches:
                    reply = _telegram_onboarding_text()
                elif len(matches) > 1:
                    reply = "Найдено несколько профилей. Отправьте email из анкеты для точной привязки."
                else:
                    candidate = matches[0]
                    email_opts = sorted(_candidate_email_options(candidate))
                    email_to = email_opts[0] if email_opts else None
                    if not email_to:
                        reply = "У кандидата не найден email. Напишите менеджеру, и мы поможем с привязкой."
                    else:
                        ok, msg = await _send_telegram_link_code(
                            db,
                            tenant_id=tenant_id,
                            chat_id=chat_id,
                            username=username,
                            candidate=candidate,
                            email_to=email_to,
                        )
                        reply = msg
            else:
                candidate = await _find_candidate_by_bind_token(db, tenant_id=tenant_id, token=bind_value)
                if candidate is None:
                    reply = "Кандидат не найден. Используйте email/телефон или проверьте токен."
                else:
                    await _link_candidate_to_telegram_chat(
                        db,
                        tenant_id=tenant_id,
                        chat_id=chat_id,
                        candidate=candidate,
                        username=username,
                    )
                    await db.commit()
                    linked_candidate_id = str(candidate.id)
                    reply = (
                        f"Готово. Telegram привязан к кандидату {_candidate_name(candidate)}.\n"
                        "Теперь доступны /status и /docs."
                    )
    elif cmd == "vacancies":
        rows = (
            await db.execute(
                sa.select(Vacancy).where(
                    Vacancy.tenant_id == tenant_id,
                    Vacancy.is_active.is_(True),
                    Vacancy.is_archived.is_(False),
                ).order_by(sa.desc(Vacancy.updated_at)).limit(5)
            )
        ).scalars().all()
        reply = _telegram_vacancies_text(rows)
    elif cmd == "apply":
        if linked_candidate is not None:
            link = _candidate_apply_url(linked_candidate)
            reply = f"Ваша анкета: {link}" if link else "Анкета недоступна. Напишите менеджеру."
        else:
            base_url = str(settings.frontend_url or "https://hostflow.cc").strip() or "https://hostflow.cc"
            reply = f"Заполнить анкету: {base_url.rstrip('/')}/public/intake"
    elif cmd in {"status", "intake", "docs", "scan", "subscribe", "unsubscribe", "lang"}:
        candidate = linked_candidate
        if candidate is None and cmd == "intake":
            try:
                candidate = await _create_candidate_from_telegram_intake(
                    db,
                    tenant_id=tenant_id,
                    chat_id=chat_id,
                    username=username,
                    sender_label=sender_label,
                    sender_address=sender_address,
                    contact_phone=contact_phone,
                )
                linked_candidate = candidate
                linked_candidate_id = str(candidate.id)
            except Exception:
                logger.exception(
                    "telegram intake candidate bootstrap failed tenant=%s chat=%s",
                    tenant_id,
                    chat_id,
                )
                reply = "Не удалось начать анкету. Попробуйте еще раз или используйте /apply."
        if candidate is None:
            reply = (
                "Профиль не найден. Вы можете:\n"
                "• начать новую анкету в Telegram: /intake\n"
                "• заполнить анкету на сайте: /apply\n"
                "• привязать существующий профиль: /bind <email|phone>"
            )
        else:
            linked_candidate_id = str(candidate.id)
            if cmd == "status":
                stage = str(getattr(candidate, "stage", "") or "").strip()
                stage_label = CANDIDATE_STAGE_LABELS.get(stage, stage) if stage else "—"
                status_value = str(getattr(candidate, "status", "") or "").strip() or stage or "—"
                status_link = _candidate_public_status_url(candidate)
                lines = [
                    f"Кандидат: {_candidate_name(candidate)}",
                    f"Этап: {stage_label}" if stage else "Этап: —",
                    f"Статус: {status_value}",
                ]
                if status_link:
                    lines.append(f"Публичная страница: {status_link}")
                reply = "\n".join(lines)
            elif cmd == "intake":
                mode = str(args[0] if args else "").strip().lower()
                if mode in {"help", "commands"}:
                    reply = _tg_intake_help_text()
                elif mode in {"status", "progress"}:
                    reply = _tg_intake_progress_text(candidate)
                elif mode == "skipped":
                    reply = _tg_intake_skipped_text(candidate)
                elif mode == "reset":
                    reply = await _tg_reset_intake_runtime(
                        db,
                        candidate=candidate,
                        chat_id=chat_id,
                        username=username,
                    )
                elif mode == "skip":
                    reply = await _tg_skip_intake_step(
                        db,
                        candidate=candidate,
                        chat_id=chat_id,
                        username=username,
                    )
                elif mode == "unskip":
                    reply = await _tg_unskip_intake_step(
                        db,
                        candidate=candidate,
                        chat_id=chat_id,
                        username=username,
                        target_step=str(args[1] if len(args) > 1 else "").strip() or None,
                    )
                else:
                    reply = await _tg_start_or_resume_intake(
                        db,
                        candidate=candidate,
                        chat_id=chat_id,
                        username=username,
                    )
            elif cmd == "docs":
                try:
                    reply = await _telegram_docs_checklist_text(
                        db,
                        tenant_id=tenant_id,
                        candidate=candidate,
                    )
                except Exception:
                    logger.exception(
                        "communications telegram docs summary failed tenant=%s candidate=%s",
                        tenant_id,
                        getattr(candidate, "id", None),
                    )
                    rows = (
                        await db.execute(
                            sa.select(Document.status, sa.func.count())
                            .where(
                                Document.tenant_id == tenant_id,
                                Document.candidate_id == str(candidate.id),
                                Document.deleted_at.is_(None),
                            )
                            .group_by(Document.status)
                        )
                    ).all()
                    reply = _telegram_docs_summary_text(rows)
            elif cmd == "scan":
                if _ensure_candidate_intake_token(candidate):
                    await db.commit()
                requested_doc = str(args[0] if args else "").strip() or None
                try:
                    reply = await _telegram_scan_command_text(
                        db,
                        tenant_id=tenant_id,
                        candidate=candidate,
                        requested_doc_type=requested_doc,
                    )
                except Exception:
                    logger.exception(
                        "communications telegram scan link failed tenant=%s candidate=%s",
                        tenant_id,
                        getattr(candidate, "id", None),
                    )
                    apply = _candidate_apply_url(candidate)
                    if apply:
                        reply = f"Откройте анкету и загрузите документы: {apply}"
                    else:
                        reply = "Сканер временно недоступен. Попробуйте позже."
            elif cmd in {"subscribe", "unsubscribe"}:
                state = _as_dict(candidate.intake_state)
                notifications = _as_dict(state.get("notifications"))
                telegram_state = _as_dict(notifications.get("telegram"))
                telegram_state["chat_id"] = chat_id
                telegram_state["subscribed"] = cmd == "subscribe"
                telegram_state["updated_at"] = now_iso
                if username:
                    telegram_state["username"] = username
                notifications["telegram"] = telegram_state
                state["notifications"] = notifications
                candidate.intake_state = state
                await db.commit()
                reply = "Уведомления в Telegram включены." if cmd == "subscribe" else "Уведомления в Telegram отключены."
            elif cmd == "lang":
                language = str(args[0] if args else "").strip().lower()
                if language not in {"ru", "en", "pl", "uk"}:
                    reply = "Поддерживаемые языки: ru, en, pl, uk. Пример: /lang pl"
                else:
                    state = _as_dict(candidate.intake_state)
                    notifications = _as_dict(state.get("notifications"))
                    telegram_state = _as_dict(notifications.get("telegram"))
                    telegram_state["chat_id"] = chat_id
                    telegram_state["language"] = language
                    telegram_state["updated_at"] = now_iso
                    if username:
                        telegram_state["username"] = username
                    notifications["telegram"] = telegram_state
                    state["notifications"] = notifications
                    candidate.intake_state = state
                    await db.commit()
                    reply = f"Язык уведомлений обновлен: {language.upper()}."

    if reply:
        try:
            await _send_candidate_telegram_reply(
                cfg=cfg,
                chat_id=chat_id,
                text=reply,
                linked=bool(linked_candidate_id),
            )
        except Exception:
            logger.exception(
                "communications telegram command reply failed tenant=%s account=%s command=%s",
                tenant_id,
                account.id,
                cmd,
            )
    return True, linked_candidate_id


def _pick_thread_recipient_address(thread: CommunicationThread) -> str | None:
    participants = _as_dict(thread.participants_json)
    recipients = participants.get("recipients")
    if isinstance(recipients, list):
        for item in recipients:
            value = str(item or "").strip()
            if value:
                return value
    senders = participants.get("senders")
    if isinstance(senders, list):
        for item in senders:
            value = str(item or "").strip()
            if value:
                return value
    return None


def _normalize_email_text(text: str | None, html: str | None) -> str:
    body = (text or "").strip()
    if body:
        return body
    if html:
        # MVP fallback: keep HTML as plain text payload to avoid losing message.
        return str(html)
    return ""


def _parse_iso_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _dispatch_attempt_count(msg: CommunicationMessage) -> int:
    dispatch = _as_dict(_as_dict(msg.payload).get("dispatch"))
    try:
        return max(0, int(dispatch.get("attempt_count") or 0))
    except Exception:
        return 0


def _dispatch_next_retry_at(msg: CommunicationMessage) -> datetime | None:
    dispatch = _as_dict(_as_dict(msg.payload).get("dispatch"))
    return _parse_iso_datetime(dispatch.get("next_retry_at"))


def _schedule_dispatch_retry(
    *,
    msg: CommunicationMessage,
    reason: str,
    actor_id: str | None,
    now: datetime,
    current_attempt: int | None = None,
    max_attempts: int = 5,
) -> bool:
    current_attempt_value = current_attempt if current_attempt is not None else _dispatch_attempt_count(msg)
    next_attempt = current_attempt_value + 1
    dispatch = _as_dict(_as_dict(msg.payload).get("dispatch"))
    dispatch.update(
        {
            "status": "retry_scheduled",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "attempt_count": next_attempt,
            "last_error_reason": reason,
        }
    )
    if next_attempt >= max_attempts:
        dispatch["status"] = "failed"
        msg.delivery_status = "failed"
        msg.error_message = reason
        msg.payload = {**_as_dict(msg.payload), "dispatch": dispatch}
        return False
    delay_seconds = min(3600, 60 * (2 ** max(0, next_attempt - 1)))
    next_retry_at = now + timedelta(seconds=delay_seconds)
    dispatch["next_retry_at"] = next_retry_at.isoformat()
    msg.delivery_status = "queued"
    msg.error_message = reason
    msg.payload = {**_as_dict(msg.payload), "dispatch": dispatch}
    return True


async def _dispatch_email_message_via_tenant_smtp(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    to_addr = (msg.recipient_address or _pick_thread_recipient_address(thread) or "").strip()
    if not to_addr:
        msg.delivery_status = "failed"
        msg.error_message = "Missing recipient address"
        return "missing_recipient"
    subject = (msg.subject or thread.subject or "").strip() or f"HostFlow {str(thread.channel).upper()} message"
    body = _normalize_email_text(msg.body_text, msg.body_html)
    if not body:
        msg.delivery_status = "failed"
        msg.error_message = "Empty email body"
        return "empty_body"

    # Preferred path: send via connected OAuth mailbox account when thread is bound to one.
    if thread.channel_account_id:
        account = await db.get(CommunicationChannelAccount, str(thread.channel_account_id))
        if account is not None and str(account.tenant_id) == str(tenant_id) and str(account.channel).lower() == "email" and bool(account.is_active):
            account_settings = _as_dict(account.settings_json)
            provider = str(account_settings.get("provider") or "").strip().lower()
            if provider in {"gmail", "microsoft_graph"}:
                oauth_json = _as_dict(account_settings.get("oauth"))
                access_token = _oauth_access_token(oauth_json)
                if not access_token or _oauth_expires_soon(oauth_json):
                    refresh_token = _oauth_refresh_token(oauth_json)
                    client_id = str(oauth_json.get("client_id") or "").strip()
                    client_secret = _oauth_client_secret(oauth_json)
                    if not refresh_token:
                        msg.delivery_status = "failed"
                        msg.error_message = "OAuth refresh token is not configured"
                        return "oauth_refresh_token_missing"
                    if not client_id:
                        msg.delivery_status = "failed"
                        msg.error_message = "OAuth client_id is not configured"
                        return "oauth_client_id_missing"
                    try:
                        token_payload = await refresh_oauth_access_token(
                            provider=provider,
                            refresh_token=refresh_token,
                            client_id=client_id,
                            client_secret=client_secret,
                            scope=str(oauth_json.get("scope") or "").strip() or None,
                        )
                    except OAuthProviderError as exc:
                        msg.delivery_status = "failed"
                        msg.error_message = str(exc)
                        return "oauth_refresh_failed"
                    oauth_next = {
                        **oauth_json,
                        "access_token": token_payload.access_token,
                        "expires_at": (_now_utc() + timedelta(seconds=int(token_payload.expires_in or 3600))).isoformat(),
                        "token_type": token_payload.token_type or str(oauth_json.get("token_type") or "Bearer"),
                        "scope": token_payload.scope or str(oauth_json.get("scope") or ""),
                        "oauth_status": "connected",
                        "last_error": None,
                        "last_refreshed_at": _now_utc().isoformat(),
                        "provider_payload": {
                            **_as_dict(oauth_json.get("provider_payload")),
                            **_as_dict(token_payload.provider_payload),
                        },
                    }
                    if token_payload.refresh_token:
                        oauth_next["refresh_token"] = token_payload.refresh_token
                    if token_payload.id_token:
                        oauth_next["id_token"] = token_payload.id_token
                    account_settings["oauth"] = _normalize_account_settings_for_store({"oauth": oauth_next}).get("oauth", oauth_next)
                    account.settings_json = account_settings
                    access_token = token_payload.access_token
                if not access_token:
                    msg.delivery_status = "failed"
                    msg.error_message = "OAuth access token is not configured"
                    return "oauth_access_token_missing"
                try:
                    provider_resp = await send_oauth_email_message(
                        provider=provider,
                        access_token=access_token,
                        to=to_addr,
                        subject=subject,
                        body_text=body,
                        body_html=msg.body_html,
                        from_address=(account.inbox_address or None),
                        reply_to=(account.inbox_address or None),
                    )
                except Exception as exc:
                    msg.delivery_status = "failed"
                    msg.error_message = str(exc)
                    msg.payload = {
                        **_as_dict(msg.payload),
                        "dispatch": {
                            "status": "failed",
                            "attempted_at": _now_utc().isoformat(),
                            "actor_user_id": actor_id,
                            "adapter": f"{provider}_oauth",
                        },
                    }
                    return "oauth_send_failed"
                now = _now_utc()
                msg.delivery_status = "sent"
                msg.sent_at = msg.sent_at or now
                msg.error_message = None
                provider_message_ref = str(_as_dict(provider_resp).get("message_ref") or "").strip() or None
                if not msg.external_message_ref:
                    msg.external_message_ref = provider_message_ref or f"{provider}_out:{thread.id}:{msg.id}"
                msg.payload = {
                    **_as_dict(msg.payload),
                    "dispatch": {
                        "status": "sent",
                        "attempted_at": now.isoformat(),
                        "actor_user_id": actor_id,
                        "adapter": f"{provider}_oauth",
                        "recipient": to_addr,
                        "provider_result": provider_resp,
                    },
                }
                return None

    try:
        await send_email_for_tenant(db, tenant_id=tenant_id, to=to_addr, subject=subject, body=body)
    except Exception as exc:
        logger.exception("communications email dispatch failed tenant=%s thread=%s msg=%s", tenant_id, thread.id, msg.id)
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": _now_utc().isoformat(),
                "actor_user_id": actor_id,
                "adapter": "tenant_smtp",
            },
        }
        return "send_failed"

    now = _now_utc()
    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref:
        msg.external_message_ref = f"smtp:{thread.id}:{msg.id}"
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "adapter": "tenant_smtp",
            "recipient": to_addr,
        },
    }
    return None


async def _dispatch_telegram_message_via_bot_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if not thread.channel_account_id:
        return "missing_channel_account"
    account = await db.get(CommunicationChannelAccount, str(thread.channel_account_id))
    if account is None or str(account.tenant_id) != tenant_id or str(account.channel).lower() != "telegram":
        return "channel_account_not_found"
    cfg = _telegram_config_from_account_settings(account)
    if cfg is None:
        return "missing_bot_token"

    chat_id = str(msg.recipient_address or thread.channel_thread_ref or "").strip()
    if not chat_id:
        recipients = _as_dict(thread.participants_json).get("recipients")
        if isinstance(recipients, list) and recipients:
            chat_id = str(recipients[0] or "").strip()
    if not chat_id:
        msg.delivery_status = "failed"
        msg.error_message = "Missing Telegram chat_id"
        return "missing_chat_id"

    text = (msg.body_text or "").strip()
    if not text:
        msg.delivery_status = "failed"
        msg.error_message = "Empty Telegram message body"
        return "empty_body"

    reply_to_id = None
    try:
        inbound_msg_id = _as_dict(msg.payload).get("reply_to_telegram_message_id")
        if inbound_msg_id is not None:
            reply_to_id = int(inbound_msg_id)
    except Exception:
        reply_to_id = None

    try:
        provider_resp = await send_telegram_text(cfg, chat_id=chat_id, text=text, reply_to_message_id=reply_to_id)
    except Exception as exc:
        logger.exception("communications telegram dispatch failed tenant=%s thread=%s msg=%s", tenant_id, thread.id, msg.id)
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": _now_utc().isoformat(),
                "actor_user_id": actor_id,
                "adapter": "telegram_bot_api",
            },
        }
        return "send_failed"

    now = _now_utc()
    result = _as_dict(provider_resp.get("result"))
    telegram_message_id = result.get("message_id")
    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref and telegram_message_id is not None:
        msg.external_message_ref = f"telegram_out:{thread.channel_thread_ref or chat_id}:{telegram_message_id}"
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "adapter": "telegram_bot_api",
            "chat_id": chat_id,
            "provider_result": provider_resp,
        },
        "telegram_message_id": telegram_message_id,
    }
    return None


async def _dispatch_whatsapp_message_via_cloud_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    now = _now_utc()
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if thread.channel != "whatsapp":
        return "unsupported_channel"

    account = await db.get(CommunicationChannelAccount, str(thread.channel_account_id or ""))
    if account is None or str(account.tenant_id) != tenant_id or str(account.channel).lower() != "whatsapp":
        msg.delivery_status = "failed"
        msg.error_message = "WhatsApp channel account is not configured"
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                "channel_account_id": thread.channel_account_id,
                "adapter": "whatsapp_cloud_api",
                "error": msg.error_message,
            },
        }
        return "missing_whatsapp_account"

    cfg = _whatsapp_config_from_account_settings(account)
    if cfg is None:
        msg.delivery_status = "failed"
        msg.error_message = "WhatsApp settings are incomplete (phone_number_id/access_token)"
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                "channel_account_id": thread.channel_account_id,
                "adapter": "whatsapp_cloud_api",
                "error": msg.error_message,
            },
        }
        return "missing_whatsapp_config"

    to_number = str(msg.recipient_address or "").strip() or str(_pick_thread_recipient_address(thread) or "").strip()
    text = _normalize_email_text(msg.body_text, msg.body_html).strip()
    if not to_number:
        msg.delivery_status = "failed"
        msg.error_message = "Recipient number is missing for WhatsApp dispatch"
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                "channel_account_id": thread.channel_account_id,
                "adapter": "whatsapp_cloud_api",
                "error": msg.error_message,
            },
        }
        return "missing_recipient"
    if not text:
        msg.delivery_status = "failed"
        msg.error_message = "Message body is empty"
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                "channel_account_id": thread.channel_account_id,
                "adapter": "whatsapp_cloud_api",
                "error": msg.error_message,
            },
        }
        return "empty_body"

    try:
        provider_resp = await send_whatsapp_text(cfg, to=to_number, text=text)
    except Exception as exc:
        logger.exception("communications whatsapp dispatch failed tenant=%s thread=%s msg=%s", tenant_id, thread.id, msg.id)
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                "channel_account_id": thread.channel_account_id,
                "adapter": "whatsapp_cloud_api",
                "error": str(exc),
            },
        }
        return "provider_error"

    messages = provider_resp.get("messages") if isinstance(provider_resp.get("messages"), list) else []
    wa_message_id = None
    if messages and isinstance(messages[0], dict):
        wa_message_id = messages[0].get("id")

    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref and wa_message_id:
        msg.external_message_ref = f"whatsapp_out:{thread.channel_thread_ref or to_number}:{wa_message_id}"
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "thread_channel": thread.channel,
            "channel_account_id": thread.channel_account_id,
            "adapter": "whatsapp_cloud_api",
        },
        "whatsapp_response": provider_resp,
        "whatsapp_message_id": wa_message_id,
    }
    return None


async def _dispatch_messenger_message_via_graph_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    now = _now_utc()
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if thread.channel != "messenger":
        return "unsupported_channel"

    account = await db.get(CommunicationChannelAccount, str(thread.channel_account_id or ""))
    if account is None or str(account.tenant_id) != tenant_id or str(account.channel).lower() != "messenger":
        return "missing_messenger_account"
    cfg, page_id = _messenger_graph_config_from_account_settings(account)
    if cfg is None or not page_id:
        return "missing_messenger_config"

    recipient_id = str(msg.recipient_address or "").strip() or str(_pick_thread_recipient_address(thread) or "").strip() or str(thread.channel_thread_ref or "").strip()
    text = _normalize_email_text(msg.body_text, msg.body_html).strip()
    if not recipient_id:
        msg.delivery_status = "failed"
        msg.error_message = "Recipient PSID is missing for Messenger dispatch"
        return "missing_recipient"
    if not text:
        msg.delivery_status = "failed"
        msg.error_message = "Message body is empty"
        return "empty_body"

    try:
        provider_resp = await send_meta_text_message(cfg, sender_id=page_id, recipient_id=recipient_id, text=text)
    except Exception as exc:
        logger.exception("communications messenger dispatch failed tenant=%s thread=%s msg=%s", tenant_id, thread.id, msg.id)
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        return "provider_error"

    message_id = provider_resp.get("message_id")
    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref and message_id:
        msg.external_message_ref = f"messenger_out:{thread.channel_thread_ref or recipient_id}:{message_id}"
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "thread_channel": thread.channel,
            "channel_account_id": thread.channel_account_id,
            "adapter": "meta_messenger_graph",
        },
        "messenger_response": provider_resp,
        "messenger_message_id": message_id,
    }
    return None


async def _dispatch_instagram_message_via_graph_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    now = _now_utc()
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if thread.channel != "instagram":
        return "unsupported_channel"

    account = await db.get(CommunicationChannelAccount, str(thread.channel_account_id or ""))
    if account is None or str(account.tenant_id) != tenant_id or str(account.channel).lower() != "instagram":
        return "missing_instagram_account"
    cfg, account_id = _instagram_graph_config_from_account_settings(account)
    if cfg is None or not account_id:
        return "missing_instagram_config"

    recipient_id = str(msg.recipient_address or "").strip() or str(_pick_thread_recipient_address(thread) or "").strip() or str(thread.channel_thread_ref or "").strip()
    text = _normalize_email_text(msg.body_text, msg.body_html).strip()
    if not recipient_id:
        msg.delivery_status = "failed"
        msg.error_message = "Recipient user id is missing for Instagram dispatch"
        return "missing_recipient"
    if not text:
        msg.delivery_status = "failed"
        msg.error_message = "Message body is empty"
        return "empty_body"

    try:
        provider_resp = await send_meta_text_message(cfg, sender_id=account_id, recipient_id=recipient_id, text=text)
    except Exception as exc:
        logger.exception("communications instagram dispatch failed tenant=%s thread=%s msg=%s", tenant_id, thread.id, msg.id)
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        return "provider_error"

    message_id = provider_resp.get("message_id")
    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref and message_id:
        msg.external_message_ref = f"instagram_out:{thread.channel_thread_ref or recipient_id}:{message_id}"
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "thread_channel": thread.channel,
            "channel_account_id": thread.channel_account_id,
            "adapter": "meta_instagram_graph",
        },
        "instagram_response": provider_resp,
        "instagram_message_id": message_id,
    }
    return None


async def _dispatch_viber_message_via_bot_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    now = _now_utc()
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if thread.channel != "viber":
        return "unsupported_channel"

    account = await db.get(CommunicationChannelAccount, str(thread.channel_account_id or ""))
    if account is None or str(account.tenant_id) != tenant_id or str(account.channel).lower() != "viber":
        return "missing_viber_account"
    cfg = _viber_config_from_account_settings(account)
    if cfg is None:
        return "missing_viber_config"

    recipient_id = str(msg.recipient_address or "").strip() or str(_pick_thread_recipient_address(thread) or "").strip() or str(thread.channel_thread_ref or "").strip()
    text = _normalize_email_text(msg.body_text, msg.body_html).strip()
    if not recipient_id:
        msg.delivery_status = "failed"
        msg.error_message = "Recipient id is missing for Viber dispatch"
        return "missing_recipient"
    if not text:
        msg.delivery_status = "failed"
        msg.error_message = "Message body is empty"
        return "empty_body"

    try:
        provider_resp = await send_viber_text_message(cfg, receiver=recipient_id, text=text)
    except Exception as exc:
        logger.exception("communications viber dispatch failed tenant=%s thread=%s msg=%s", tenant_id, thread.id, msg.id)
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        return "provider_error"

    message_token = provider_resp.get("message_token")
    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref and message_token:
        msg.external_message_ref = f"viber_out:{thread.channel_thread_ref or recipient_id}:{message_token}"
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "thread_channel": thread.channel,
            "channel_account_id": thread.channel_account_id,
            "adapter": "viber_bot_api",
        },
        "viber_response": provider_resp,
        "viber_message_token": message_token,
    }
    return None


def _touch_thread_from_message(thread: CommunicationThread, msg: CommunicationMessage, *, tenant: Tenant | None = None) -> None:
    now = _now_utc()
    ts = msg.sent_at or msg.delivered_at or msg.read_at or msg.created_at or now
    thread.last_message_at = ts
    preview = (msg.body_text or msg.subject or "").strip()
    if preview:
        thread.last_message_preview = preview[:500]
    if msg.direction == "inbound":
        thread.last_inbound_at = ts
        payload = _as_dict(msg.payload)
        is_telegram_command = bool(payload.get("telegram_command"))
        text = str(msg.body_text or "").strip()
        is_slash_command = str(msg.channel or "").lower() == "telegram" and text.startswith("/")
        if msg.read_at is None and not is_telegram_command and not is_slash_command:
            thread.unread_count = int(thread.unread_count or 0) + 1
    elif msg.direction == "outbound":
        thread.last_outbound_at = ts
        if thread.direction_hint in (None, "", "inbound"):
            thread.direction_hint = "mixed" if thread.direction_hint else "outbound"
    if msg.direction == "inbound" and thread.direction_hint in (None, "", "outbound"):
        thread.direction_hint = "mixed" if thread.direction_hint == "outbound" else "inbound"
    _apply_thread_sla_policy_from_message(thread, msg, tenant)
    thread.updated_at = now


async def _resolve_thread_sla_alerts(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
    close_mode: str = "done",
    now: datetime | None = None,
) -> None:
    from backend.app.models.reminder import Reminder, ReminderStatus
    from backend.app.models.user_notification import UserNotification

    ts = now or _now_utc()
    if close_mode == "cancelled":
        await db.execute(
            sa.update(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "communication_thread",
                Reminder.entity_id == str(thread_id),
                Reminder.type == "communications_sla_overdue",
                Reminder.status.in_([ReminderStatus.new, ReminderStatus.pending, ReminderStatus.overdue]),
            )
            .values(
                status=ReminderStatus.cancelled,
                cancelled_at=ts,
                completed_at=ts,
                updated_at=ts,
            )
        )
    else:
        await db.execute(
            sa.update(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "communication_thread",
                Reminder.entity_id == str(thread_id),
                Reminder.type == "communications_sla_overdue",
                Reminder.status.in_([ReminderStatus.new, ReminderStatus.pending, ReminderStatus.overdue]),
            )
            .values(
                status=ReminderStatus.done,
                completed_at=ts,
                updated_at=ts,
            )
        )

    await db.execute(
        sa.update(UserNotification)
        .where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.event_type == "communications_sla_overdue",
            UserNotification.entity_type == "communication_thread",
            UserNotification.entity_id == str(thread_id),
            UserNotification.is_read.is_(False),
        )
        .values(is_read=True, read_at=ts, updated_at=ts)
    )


@router.get("/threads", response_model=CommunicationThreadListResponse)
@router.get("/threads/", response_model=CommunicationThreadListResponse, include_in_schema=False)
async def list_threads(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    channel: str | None = Query(None),
    status_filter: List[str] | None = Query(None),
    assignee_id: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    include_archived: bool = Query(False),
    q: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationThreadListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if channel:
        await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(channel))
    else:
        await _require_any_comm_feature(db, tenant_id=tenant_id, current_user=current_user, features=["messages", "email"])

    stmt = sa.select(CommunicationThread).where(CommunicationThread.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationThread).where(CommunicationThread.tenant_id == tenant_id)

    filters = []
    if channel:
        filters.append(CommunicationThread.channel == channel)
    if status_filter:
        filters.append(CommunicationThread.status.in_([str(s) for s in status_filter]))
    if assignee_id:
        filters.append(CommunicationThread.assignee_id == assignee_id)
    if entity_type:
        filters.append(CommunicationThread.entity_type == entity_type)
    if entity_id:
        filters.append(CommunicationThread.entity_id == entity_id)
    if not include_archived:
        filters.append(CommunicationThread.is_archived.is_(False))
    if q:
        like = f"%{q.strip().lower()}%"
        filters.append(
            sa.or_(
                sa.func.lower(sa.func.coalesce(CommunicationThread.subject, "")).like(like),
                sa.func.lower(sa.func.coalesce(CommunicationThread.last_message_preview, "")).like(like),
                sa.func.lower(sa.cast(sa.func.coalesce(CommunicationThread.channel_thread_ref, ""), sa.String)).like(like),
            )
        )

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    stmt = stmt.order_by(
        sa.desc(sa.func.coalesce(CommunicationThread.last_message_at, CommunicationThread.updated_at)),
        sa.desc(CommunicationThread.updated_at),
    ).limit(limit).offset(offset)

    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationThreadListResponse(items=[_thread_out(r) for r in rows], total=total)


@router.get("/message-templates", response_model=CommunicationMessageTemplateListResponse)
async def list_message_templates(
    target: str = Query("messages"),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationMessageTemplateListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    normalized_target = str(target or "messages").strip().lower()
    if normalized_target not in {"messages", "email"}:
        normalized_target = "messages"
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=normalized_target)
    tenant = await _get_tenant_or_404(db, tenant_id)
    user_id = str(getattr(current_user, "sub", "") or "").strip() or None
    items = _message_templates_for_user(tenant, user_id=user_id, target=normalized_target)
    return CommunicationMessageTemplateListResponse(items=items, total=len(items))


@router.post("/threads", response_model=CommunicationThreadOut, status_code=status.HTTP_201_CREATED)
async def create_thread(
    body: CommunicationThreadCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationThreadOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(body.channel))
    thread = CommunicationThread(
        tenant_id=tenant_id,
        channel=body.channel,
        channel_account_id=body.channel_account_id,
        channel_thread_ref=body.channel_thread_ref,
        subject=body.subject,
        status=body.status,
        direction_hint=body.direction_hint,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        linked_company_id=body.linked_company_id,
        linked_candidate_id=body.linked_candidate_id,
        owner_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        assignee_id=body.assignee_id,
        priority=body.priority,
        participants_json=body.participants_json,
        tags_json=body.tags_json,
        thread_meta=body.thread_meta,
        queue_assigned_by="manual" if body.assignee_id else None,
    )
    db.add(thread)
    if body.auto_assign and not body.assignee_id:
        tenant = await _get_tenant_or_404(db, tenant_id)
        await allocate_thread(
            db,
            tenant=tenant,
            thread=thread,
            actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        )
    await db.commit()
    await db.refresh(thread)
    return _thread_out(thread)


@router.get("/threads/{thread_id}", response_model=CommunicationThreadDetailResponse)
async def get_thread(
    thread_id: str,
    messages_limit: int = Query(50, ge=1, le=500),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationThreadDetailResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    messages_stmt = (
        sa.select(CommunicationMessage)
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.thread_id == thread_id,
        )
        .order_by(sa.asc(CommunicationMessage.created_at))
        .limit(messages_limit)
    )
    msgs = (await db.execute(messages_stmt)).scalars().all()
    return CommunicationThreadDetailResponse(thread=_thread_out(thread), messages=[_message_out(m) for m in msgs])


@router.patch("/threads/{thread_id}", response_model=CommunicationThreadOut)
async def patch_thread(
    thread_id: str,
    body: CommunicationThreadPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationThreadOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    patch = body.model_dump(exclude_unset=True)
    meta_patch = patch.pop("thread_meta", None)
    for key, value in patch.items():
        setattr(thread, key, value)
    if meta_patch is not None:
        merged_meta = _deep_merge_dict(_as_dict(thread.thread_meta), _as_dict(meta_patch))
        merged_sla_policy = _as_dict(merged_meta.get("sla_policy"))
        merged_ops = _as_dict(merged_meta.get("ops"))
        now = _now_utc()
        muted = bool(merged_sla_policy.get("muted") or merged_meta.get("sla_muted"))
        merged_sla_policy["muted"] = muted
        merged_meta["sla_muted"] = muted
        if muted and not merged_sla_policy.get("muted_at"):
            merged_sla_policy["muted_at"] = now.isoformat()
        if not muted:
            merged_sla_policy.pop("muted_at", None)
        no_reply_needed = bool(merged_sla_policy.get("no_reply_needed") or merged_meta.get("no_reply_needed"))
        merged_sla_policy["no_reply_needed"] = no_reply_needed
        merged_meta["no_reply_needed"] = no_reply_needed
        if muted:
            await _resolve_thread_sla_alerts(
                db,
                tenant_id=tenant_id,
                thread_id=str(thread.id),
                close_mode="cancelled",
            )
        if no_reply_needed:
            thread.sla_due_at = None
            if not merged_sla_policy.get("no_reply_needed_at"):
                merged_sla_policy["no_reply_needed_at"] = now.isoformat()
            merged_sla_policy.pop("snoozed_until", None)
            await _resolve_thread_sla_alerts(
                db,
                tenant_id=tenant_id,
                thread_id=str(thread.id),
                close_mode="cancelled",
            )
        else:
            merged_sla_policy.pop("no_reply_needed_at", None)
            snoozed_until_raw = str(merged_sla_policy.get("snoozed_until") or "").strip()
            if snoozed_until_raw:
                snoozed_until = None
                try:
                    snoozed_until = datetime.fromisoformat(snoozed_until_raw.replace("Z", "+00:00"))
                except Exception:
                    snoozed_until = None
                if snoozed_until is not None and snoozed_until.tzinfo is None:
                    snoozed_until = snoozed_until.replace(tzinfo=timezone.utc)
                if snoozed_until is not None and snoozed_until > now:
                    thread.sla_due_at = snoozed_until
                    merged_sla_policy["snoozed_until"] = snoozed_until.isoformat()
                    await _resolve_thread_sla_alerts(
                        db,
                        tenant_id=tenant_id,
                        thread_id=str(thread.id),
                        close_mode="cancelled",
                    )
                else:
                    merged_sla_policy.pop("snoozed_until", None)

        ops_mode = str(merged_ops.get("mode") or "").strip().lower()
        if ops_mode == "escalated":
            escalation = _as_dict(merged_ops.get("escalation"))
            reason = str(escalation.get("reason") or "").strip()
            target = _as_dict(escalation.get("target"))
            has_target = any(
                str(target.get(k) or "").strip()
                for k in ("queue", "role", "user_id")
            )
            if not reason:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "ops_escalation_reason_required",
                        "message": "Escalation reason is required for escalated mode",
                    },
                )
            if not has_target:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "ops_escalation_target_required",
                        "message": "Escalation target is required for escalated mode",
                    },
                )
            queue_target = str(target.get("queue") or "").strip()
            if queue_target:
                allowed_targets = _tenant_sla_escalation_targets(tenant)
                if allowed_targets and queue_target not in allowed_targets:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "ops_escalation_target_unknown_queue",
                            "message": "Escalation queue target is not allowed by tenant SLA settings",
                            "allowed_targets": sorted(allowed_targets),
                        },
                    )
            role_target = str(target.get("role") or "").strip().lower()
            if role_target:
                if not re.match(r"^[a-z][a-z0-9_-]{1,63}$", role_target):
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "ops_escalation_target_invalid_role",
                            "message": "Escalation role target has invalid format",
                            "role": role_target,
                        },
                    )
                allowed_roles = _tenant_comm_allowed_roles(tenant)
                if allowed_roles and role_target not in allowed_roles:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "ops_escalation_target_unknown_role",
                            "message": "Escalation role target is not allowed by tenant communications access settings",
                            "allowed_roles": sorted(allowed_roles),
                        },
                    )
                target["role"] = role_target
            user_target = str(target.get("user_id") or "").strip()
            if user_target:
                try:
                    UUID(user_target)
                except Exception:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "ops_escalation_target_invalid_user_id",
                            "message": "Escalation user target must be a valid UUID",
                            "user_id": user_target,
                        },
                    )
                user_row = (
                    await db.execute(
                        sa.select(User.id)
                        .where(
                            User.id == user_target,
                            User.tenant_id == tenant_id,
                            User.is_active.is_(True),
                        )
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if user_row is None:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "ops_escalation_target_unknown_user",
                            "message": "Escalation user target does not belong to current tenant or is inactive",
                            "user_id": user_target,
                        },
                    )
            escalation["reason"] = reason
            escalation["target"] = target
            escalation["escalated_at"] = str(escalation.get("escalated_at") or now.isoformat())
            merged_ops["escalation"] = escalation
            if str(thread.priority or "").strip().lower() != "high":
                thread.priority = "high"

        if ops_mode in ("later", "paused"):
            paused_until_raw = str(merged_ops.get("paused_until") or "").strip()
            paused_until = None
            if paused_until_raw:
                try:
                    paused_until = datetime.fromisoformat(paused_until_raw.replace("Z", "+00:00"))
                except Exception:
                    paused_until = None
            if paused_until is not None and paused_until.tzinfo is None:
                paused_until = paused_until.replace(tzinfo=timezone.utc)
            if paused_until is not None and paused_until > now:
                merged_ops["mode"] = "later"
                merged_ops["paused_until"] = paused_until.isoformat()
                merged_sla_policy["no_reply_needed"] = False
                merged_meta["no_reply_needed"] = False
                merged_sla_policy["snoozed_until"] = paused_until.isoformat()
                thread.sla_due_at = paused_until
                await _resolve_thread_sla_alerts(
                    db,
                    tenant_id=tenant_id,
                    thread_id=str(thread.id),
                    close_mode="cancelled",
                )
            else:
                merged_ops["mode"] = "in_work"
                merged_ops.pop("paused_until", None)
                merged_sla_policy.pop("snoozed_until", None)
        else:
            merged_ops.pop("paused_until", None)

        merged_meta["ops"] = merged_ops
        merged_meta["sla_policy"] = merged_sla_policy
        thread.thread_meta = merged_meta
    thread.updated_at = _now_utc()
    await db.commit()
    await db.refresh(thread)
    return _thread_out(thread)


@router.get("/threads/{thread_id}/messages", response_model=CommunicationMessageListResponse)
async def list_thread_messages(
    thread_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationMessageListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationMessage).where(
        CommunicationMessage.tenant_id == tenant_id,
        CommunicationMessage.thread_id == thread_id,
    )
    stmt = (
        sa.select(CommunicationMessage)
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.thread_id == thread_id,
        )
        .order_by(sa.asc(CommunicationMessage.created_at))
        .limit(limit)
        .offset(offset)
    )
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationMessageListResponse(items=[_message_out(m) for m in rows], total=total)


@router.post("/threads/{thread_id}/messages", response_model=CommunicationMessageOut, status_code=status.HTTP_201_CREATED)
async def create_thread_message(
    thread_id: str,
    body: CommunicationMessageCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationMessageOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    now = _now_utc()
    msg = CommunicationMessage(
        tenant_id=tenant_id,
        thread_id=thread_id,
        channel=thread.channel,
        message_type=body.message_type,
        direction=body.direction,
        sender_type=body.sender_type or ("user" if body.direction == "outbound" else body.sender_type),
        sender_id=body.sender_id or (str(current_user.sub) if body.direction == "outbound" and getattr(current_user, "sub", None) else None),
        sender_label=body.sender_label,
        sender_address=body.sender_address,
        recipient_type=body.recipient_type,
        recipient_id=body.recipient_id,
        recipient_label=body.recipient_label,
        recipient_address=body.recipient_address,
        subject=body.subject,
        body_text=body.body_text,
        body_html=body.body_html,
        attachments_json=body.attachments_json,
        payload=body.payload,
        external_message_ref=body.external_message_ref,
        delivery_status=body.delivery_status,
        is_internal_note=body.is_internal_note,
        sent_at=body.sent_at if body.sent_at is not None else (now if body.direction == "outbound" and body.delivery_status in {"sent", "delivered", "read"} else None),
        delivered_at=body.delivered_at,
        read_at=body.read_at,
    )
    db.add(msg)
    await db.flush()
    _touch_thread_from_message(thread, msg, tenant=tenant)
    await db.commit()
    await db.refresh(msg)
    return _message_out(msg)


@router.post("/messages/{message_id}/dispatch", response_model=CommunicationDispatchResponse)
async def dispatch_message(
    message_id: str,
    body: CommunicationDispatchRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationDispatchResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    msg = await db.get(CommunicationMessage, message_id)
    if msg is None or str(msg.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Message not found")
    thread = await _get_thread_or_404(db, tenant_id, str(msg.thread_id))
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    if thread.channel == "email" and not body.simulate_failure:
        reason = await _dispatch_email_message_via_tenant_smtp(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    elif thread.channel == "telegram" and not body.simulate_failure:
        reason = await _dispatch_telegram_message_via_bot_api(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    elif thread.channel == "whatsapp" and not body.simulate_failure:
        reason = await _dispatch_whatsapp_message_via_cloud_api(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    elif thread.channel == "messenger" and not body.simulate_failure:
        reason = await _dispatch_messenger_message_via_graph_api(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    elif thread.channel == "instagram" and not body.simulate_failure:
        reason = await _dispatch_instagram_message_via_graph_api(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    elif thread.channel == "viber" and not body.simulate_failure:
        reason = await _dispatch_viber_message_via_bot_api(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    else:
        reason = _mock_dispatch_outbound_message(
            thread=thread,
            msg=msg,
            actor_id=actor_id,
            mark_delivered=bool(body.mark_delivered),
            simulate_failure=bool(body.simulate_failure),
            provider_message_ref=body.provider_message_ref,
            provider_payload=body.provider_payload,
        )
    if reason is None:
        _touch_thread_from_message(thread, msg)
        await _resolve_thread_sla_alerts(
            db,
            tenant_id=tenant_id,
            thread_id=str(thread.id),
            close_mode="done",
        )
    thread.updated_at = _now_utc()
    await db.commit()
    await db.refresh(msg)
    await db.refresh(thread)
    return CommunicationDispatchResponse(
        dispatched=reason is None,
        message=_message_out(msg),
        thread=_thread_out(thread),
        reason=reason,
    )


@router.post("/dispatch/queued", response_model=CommunicationDispatchQueuedResponse)
async def dispatch_queued_messages(
    body: CommunicationDispatchQueuedRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationDispatchQueuedResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if body.channel:
        await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(body.channel))
    elif body.only_email:
        await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="email")
    else:
        await _require_any_comm_feature(db, tenant_id=tenant_id, current_user=current_user, features=["messages", "email"])
    fetch_limit = max(body.limit, min(body.limit * 4, 800))
    stmt = (
        sa.select(CommunicationMessage)
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.direction == "outbound",
            CommunicationMessage.delivery_status == "queued",
            CommunicationMessage.is_internal_note.is_(False),
        )
        .order_by(sa.asc(CommunicationMessage.created_at))
        .limit(fetch_limit)
    )
    if body.channel:
        stmt = stmt.where(CommunicationMessage.channel == body.channel)
    elif body.only_email:
        stmt = stmt.where(CommunicationMessage.channel == "email")
    rows = (await db.execute(stmt)).scalars().all()

    items: List[CommunicationDispatchResponse] = []
    dispatched_count = 0
    failed_count = 0
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None

    thread_cache: Dict[str, CommunicationThread] = {}
    attempted_count = 0
    now_ref = _now_utc()
    for msg in rows:
        if attempted_count >= body.limit:
            break
        next_retry_at = _dispatch_next_retry_at(msg)
        if next_retry_at is not None and next_retry_at > now_ref:
            continue
        attempted_count += 1
        attempt_before = _dispatch_attempt_count(msg)
        thread = thread_cache.get(str(msg.thread_id))
        if thread is None:
            thread = await _get_thread_or_404(db, tenant_id, str(msg.thread_id))
            thread_cache[str(thread.id)] = thread
        if thread.channel == "email" and not body.simulate_failure:
            reason = await _dispatch_email_message_via_tenant_smtp(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        elif thread.channel == "telegram" and not body.simulate_failure:
            reason = await _dispatch_telegram_message_via_bot_api(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        elif thread.channel == "whatsapp" and not body.simulate_failure:
            reason = await _dispatch_whatsapp_message_via_cloud_api(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        elif thread.channel == "messenger" and not body.simulate_failure:
            reason = await _dispatch_messenger_message_via_graph_api(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        elif thread.channel == "instagram" and not body.simulate_failure:
            reason = await _dispatch_instagram_message_via_graph_api(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        elif thread.channel == "viber" and not body.simulate_failure:
            reason = await _dispatch_viber_message_via_bot_api(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        else:
            reason = _mock_dispatch_outbound_message(
                thread=thread,
                msg=msg,
                actor_id=actor_id,
                mark_delivered=bool(body.mark_delivered),
                simulate_failure=bool(body.simulate_failure),
                provider_message_ref=None,
                provider_payload={"batch": True},
            )
        if reason is None:
            dispatched_count += 1
            _touch_thread_from_message(thread, msg)
            await _resolve_thread_sla_alerts(
                db,
                tenant_id=tenant_id,
                thread_id=str(thread.id),
                close_mode="done",
            )
        else:
            failed_count += 1
            _schedule_dispatch_retry(
                msg=msg,
                reason=reason,
                actor_id=actor_id,
                now=_now_utc(),
                current_attempt=attempt_before,
            )
        thread.updated_at = _now_utc()
        items.append(
            CommunicationDispatchResponse(
                dispatched=reason is None,
                message=_message_out(msg),
                thread=_thread_out(thread),
                reason=reason,
            )
        )

    await db.commit()
    return CommunicationDispatchQueuedResponse(
        processed=attempted_count,
        dispatched=dispatched_count,
        failed=failed_count,
        items=items,
    )


@router.patch("/messages/{message_id}/delivery-status", response_model=CommunicationMessageOut)
async def patch_message_delivery_status(
    message_id: str,
    body: CommunicationDeliveryStatusPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationMessageOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    msg = await db.get(CommunicationMessage, message_id)
    if msg is None or str(msg.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Message not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(msg.channel))  # type: ignore[arg-type]
    if body.external_message_ref:
        msg.external_message_ref = body.external_message_ref
    msg.delivery_status = body.delivery_status
    msg.error_message = body.error_message
    if body.delivery_status in {"sent", "delivered", "read"} and msg.sent_at is None:
        msg.sent_at = _now_utc()
    if body.delivery_status in {"delivered", "read"}:
        msg.delivered_at = body.delivered_at or msg.delivered_at or _now_utc()
    if body.delivery_status == "read":
        msg.read_at = body.read_at or msg.read_at or _now_utc()
    if body.provider_payload:
        msg.payload = {**_as_dict(msg.payload), "provider_callback": body.provider_payload}
    await db.commit()
    await db.refresh(msg)
    return _message_out(msg)


@router.get(
    "/scheduler/status",
    response_model=CommunicationSchedulerStatusOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def get_communications_scheduler_status(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationSchedulerStatusOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="communicationsAdmin")
    data = scheduler_runtime_status()
    return CommunicationSchedulerStatusOut(**data)


@router.post(
    "/scheduler/run-now",
    response_model=CommunicationSchedulerRunNowResponse,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def run_communications_scheduler_now(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationSchedulerRunNowResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="communicationsAdmin")
    data = await run_scheduler_tick_once()
    return CommunicationSchedulerRunNowResponse(ok=True, status=CommunicationSchedulerStatusOut(**data))


@router.post("/email/worker/dispatch", response_model=CommunicationDispatchQueuedResponse)
async def run_email_dispatch_worker(
    body: CommunicationEmailWorkerDispatchRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationDispatchQueuedResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="email")
    return await dispatch_queued_messages(
        CommunicationDispatchQueuedRequest(
            limit=body.limit,
            only_email=True,
            mark_delivered=body.mark_delivered,
            simulate_failure=False,
        ),
        db_tenant=db_tenant,
        current_user=current_user,
    )


@router.post("/email/worker/poll", response_model=CommunicationEmailWorkerPollResponse)
async def run_email_poll_worker(
    body: CommunicationEmailWorkerPollRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationEmailWorkerPollResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="email")
    stmt = sa.select(CommunicationChannelAccount).where(
        CommunicationChannelAccount.tenant_id == tenant_id,
        CommunicationChannelAccount.channel == "email",
        CommunicationChannelAccount.is_active.is_(True),
    )
    if body.only_account_id:
        stmt = stmt.where(CommunicationChannelAccount.id == body.only_account_id)
    accounts = (await db.execute(stmt.order_by(sa.asc(CommunicationChannelAccount.account_label)))).scalars().all()

    results: List[Dict[str, Any]] = []
    supported_accounts = 0
    unsupported_accounts = 0
    ingested_messages = 0
    created_threads = 0
    skipped_messages = 0

    for account in accounts:
        settings_json = _as_dict(account.settings_json)
        provider = str(settings_json.get("provider") or "manual").strip().lower()
        mock_queue = settings_json.get("mock_inbox")
        if provider not in {"manual", "manual-test", "imap_mock", "imap", "gmail", "microsoft_graph"}:
            unsupported_accounts += 1
            results.append(
                {
                    "account_id": str(account.id),
                    "account_label": account.account_label,
                    "provider": provider,
                    "status": "unsupported_provider",
                    "processed": 0,
                }
            )
            continue

        supported_accounts += 1
        queue_list = [x for x in (mock_queue if isinstance(mock_queue, list) else []) if isinstance(x, dict)]
        fetched_items: List[Dict[str, Any]]
        if provider == "imap":
            try:
                imap_cfg = _imap_config_from_account_settings(account)
                if imap_cfg is None:
                    raise RuntimeError("IMAP settings are incomplete (host/user/password)")
                poll_result = await poll_imap_messages(imap_cfg, limit=body.limit_per_account)
                fetched_items = [x for x in (poll_result.get("items") if isinstance(poll_result, dict) else []) or [] if isinstance(x, dict)]
                settings_json = _as_dict(account.settings_json)
                sync = _as_dict(settings_json.get("sync"))
                sync.update(
                    {
                        "status": "ok",
                        "last_sync_at": _now_utc().isoformat(),
                        "mode": "imap_poll_worker",
                        "provider_result": {
                            "matched": poll_result.get("matched"),
                            "returned": poll_result.get("returned"),
                            "folder": poll_result.get("folder"),
                            "search_criteria": poll_result.get("search_criteria"),
                        },
                        "last_error": None,
                    }
                )
                settings_json["sync"] = sync
                account.settings_json = settings_json
                await db.commit()
            except Exception as exc:
                unsupported_accounts += 0
                skipped_messages += 1
                settings_json = _as_dict(account.settings_json)
                sync = _as_dict(settings_json.get("sync"))
                sync.update(
                    {
                        "status": "error",
                        "last_sync_at": _now_utc().isoformat(),
                        "mode": "imap_poll_worker",
                        "last_error": str(exc),
                    }
                )
                settings_json["sync"] = sync
                account.settings_json = settings_json
                await db.commit()
                logger.exception("communications imap poll failed account=%s", account.id)
                results.append(
                    {
                        "account_id": str(account.id),
                        "account_label": account.account_label,
                        "provider": provider,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                continue
        elif provider in {"gmail", "microsoft_graph"}:
            try:
                oauth_json = _as_dict(settings_json.get("oauth"))
                access_token = _oauth_access_token(oauth_json)
                if not access_token or _oauth_expires_soon(oauth_json):
                    refresh_token = _oauth_refresh_token(oauth_json)
                    client_id = str(oauth_json.get("client_id") or "").strip()
                    client_secret = _oauth_client_secret(oauth_json)
                    if not refresh_token:
                        raise RuntimeError("OAuth refresh token is not configured")
                    if not client_id:
                        raise RuntimeError("OAuth client_id is required")
                    token_payload = await refresh_oauth_access_token(
                        provider=provider,
                        refresh_token=refresh_token,
                        client_id=client_id,
                        client_secret=client_secret,
                        scope=str(oauth_json.get("scope") or "").strip() or None,
                    )
                    oauth_next = {
                        **oauth_json,
                        "access_token": token_payload.access_token,
                        "expires_at": (_now_utc() + timedelta(seconds=int(token_payload.expires_in or 3600))).isoformat(),
                        "token_type": token_payload.token_type or str(oauth_json.get("token_type") or "Bearer"),
                        "scope": token_payload.scope or str(oauth_json.get("scope") or ""),
                        "oauth_status": "connected",
                        "last_error": None,
                        "last_refreshed_at": _now_utc().isoformat(),
                        "provider_payload": {
                            **_as_dict(oauth_json.get("provider_payload")),
                            **_as_dict(token_payload.provider_payload),
                        },
                    }
                    if token_payload.refresh_token:
                        oauth_next["refresh_token"] = token_payload.refresh_token
                    if token_payload.id_token:
                        oauth_next["id_token"] = token_payload.id_token
                    settings_json["oauth"] = _normalize_account_settings_for_store({"oauth": oauth_next}).get("oauth", oauth_next)
                    access_token = token_payload.access_token

                if not access_token:
                    raise RuntimeError("OAuth access token is missing")
                cursor_map = _as_dict(settings_json.get("sync_cursors"))
                fetched_items = []
                oauth_folder_results: Dict[str, Dict[str, Any]] = {}
                for folder in ("inbox", "sent"):
                    cursor_key = f"{folder}_cursor"
                    cursor_row = _as_dict(cursor_map.get(cursor_key))
                    cursor = str(cursor_row.get("value") or "").strip() or None
                    oauth_poll_result = await poll_oauth_mailbox_messages(
                        provider=provider,
                        access_token=access_token,
                        limit=body.limit_per_account,
                        cursor=cursor,
                        folder=folder,
                    )
                    oauth_folder_results[folder] = {
                        "returned": oauth_poll_result.returned,
                        "next_cursor": oauth_poll_result.next_cursor,
                        "raw": oauth_poll_result.raw,
                    }
                    for row in oauth_poll_result.items:
                        if not isinstance(row, dict):
                            continue
                        fetched_items.append({**row, "_mailbox_source": folder})
                    if oauth_poll_result.next_cursor is not None:
                        cursor_map[cursor_key] = {
                            "value": oauth_poll_result.next_cursor,
                            "meta": {"provider": provider, "source": f"oauth_poll_worker:{folder}"},
                            "updated_at": _now_utc().isoformat(),
                        }
                sync = _as_dict(settings_json.get("sync"))
                sync.update(
                    {
                        "status": "ok",
                        "last_sync_at": _now_utc().isoformat(),
                        "mode": f"{provider}_poll_worker",
                        "provider_result": oauth_folder_results,
                        "last_error": None,
                    }
                )
                settings_json["sync"] = sync
                settings_json["sync_cursors"] = cursor_map
                account.settings_json = settings_json
                await db.commit()
            except (OAuthMailboxPollError, OAuthProviderError, Exception) as exc:
                skipped_messages += 1
                try:
                    await db.rollback()
                except Exception:
                    pass
                settings_json = _as_dict(account.settings_json)
                oauth_json = _as_dict(settings_json.get("oauth"))
                oauth_json["last_error"] = str(exc)
                settings_json["oauth"] = oauth_json
                sync = _as_dict(settings_json.get("sync"))
                sync.update(
                    {
                        "status": "error",
                        "last_sync_at": _now_utc().isoformat(),
                        "mode": f"{provider}_poll_worker",
                        "last_error": str(exc),
                    }
                )
                settings_json["sync"] = sync
                account.settings_json = settings_json
                await db.commit()
                logger.exception("communications oauth email poll failed account=%s provider=%s", account.id, provider)
                results.append(
                    {
                        "account_id": str(account.id),
                        "account_label": account.account_label,
                        "provider": provider,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                continue
        else:
            fetched_items = queue_list

        if not fetched_items:
            results.append(
                {
                    "account_id": str(account.id),
                    "account_label": account.account_label,
                    "provider": provider,
                    "status": "empty",
                    "processed": 0,
                }
            )
            continue

        processed = 0
        consumed = 0
        source_items = fetched_items[: body.limit_per_account]
        for raw in source_items:
            consumed += 1
            try:
                mailbox_source = str(raw.get("_mailbox_source") or "inbox").strip().lower()
                if mailbox_source == "sent":
                    created_thread, duplicate = await _ingest_email_outbound_from_mailbox(
                        db,
                        tenant_id=tenant_id,
                        channel_account_id=str(account.id),
                        provider=provider,
                        provider_thread_ref=str(raw.get("provider_thread_ref") or "") or None,
                        external_message_ref=str(raw.get("external_message_ref") or "") or None,
                        subject=str(raw.get("subject") or "") or None,
                        from_address=str(raw.get("from_address") or "") or account.inbox_address or None,
                        to_address=str(raw.get("to_address") or "") or None,
                        to_name=str(raw.get("to_name") or "") or None,
                        text=(raw.get("text") if isinstance(raw.get("text"), str) else None),
                        html=(raw.get("html") if isinstance(raw.get("html"), str) else None),
                        headers=_as_dict(raw.get("headers")),
                        payload=_as_dict(raw.get("payload")),
                        sent_at=_coerce_datetime(raw.get("received_at")),
                        tenant=tenant,
                    )
                    processed += 1
                    ingested_messages += 1
                    if created_thread:
                        created_threads += 1
                    if duplicate:
                        skipped_messages += 1
                else:
                    payload = EmailIngestRequest(
                        channel_account_id=str(account.id),
                        provider=provider,
                        provider_thread_ref=str(raw.get("provider_thread_ref") or "") or None,
                        external_message_ref=str(raw.get("external_message_ref") or "") or None,
                        subject=str(raw.get("subject") or "") or None,
                        from_address=str(raw.get("from_address") or "") or None,
                        from_name=str(raw.get("from_name") or "") or None,
                        to_address=str(raw.get("to_address") or account.inbox_address or "") or None,
                        to_name=str(raw.get("to_name") or "") or None,
                        cc=[str(x) for x in raw.get("cc", []) if x is not None] if isinstance(raw.get("cc"), list) else [],
                        bcc=[str(x) for x in raw.get("bcc", []) if x is not None] if isinstance(raw.get("bcc"), list) else [],
                        text=(raw.get("text") if isinstance(raw.get("text"), str) else None),
                        html=(raw.get("html") if isinstance(raw.get("html"), str) else None),
                        headers=_as_dict(raw.get("headers")),
                        payload=_as_dict(raw.get("payload")),
                        entity_type=str(raw.get("entity_type") or "") or None,
                        entity_id=str(raw.get("entity_id") or "") or None,
                        linked_candidate_id=str(raw.get("linked_candidate_id") or "") or None,
                        linked_company_id=str(raw.get("linked_company_id") or "") or None,
                        assignee_id=str(raw.get("assignee_id") or "") or None,
                        auto_assign=bool(raw.get("auto_assign", True)),
                    )
                    resp = await ingest_email(payload, db_tenant=(db, tenant_uuid), current_user=current_user)
                    processed += 1
                    ingested_messages += 1
                    if resp.created_thread:
                        created_threads += 1
                    if resp.duplicate_message:
                        skipped_messages += 1
            except Exception as exc:
                skipped_messages += 1
                logger.exception("communications email poll ingest failed account=%s", account.id)
                results.append(
                    {
                        "account_id": str(account.id),
                        "account_label": account.account_label,
                        "provider": provider,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                break

        # Remove consumed messages from mock queue regardless of duplicates; they were processed.
        remaining = queue_list[consumed:] if provider in {"manual", "manual-test", "imap_mock"} else []
        if provider in {"manual", "manual-test", "imap_mock"}:
          settings_json["mock_inbox"] = remaining
          sync = _as_dict(settings_json.get("sync"))
          sync.update(
              {
                  "status": "ok",
                  "last_sync_at": _now_utc().isoformat(),
                  "last_polled_count": processed,
                  "remaining_mock_queue": len(remaining),
                  "mode": "mock_poll_worker",
                  "last_error": None,
              }
          )
          settings_json["sync"] = sync
          account.settings_json = settings_json
          await db.commit()

        results.append(
            {
                "account_id": str(account.id),
                "account_label": account.account_label,
                "provider": provider,
                "status": "ok",
                "processed": processed,
                "remaining": len(remaining) if provider in {"manual", "manual-test", "imap_mock"} else None,
            }
        )

    return CommunicationEmailWorkerPollResponse(
        polled_accounts=len(accounts),
        supported_accounts=supported_accounts,
        ingested_messages=ingested_messages,
        created_threads=created_threads,
        skipped_messages=skipped_messages,
        unsupported_accounts=unsupported_accounts,
        items=results,
    )


@router.post("/threads/{thread_id}/read", response_model=CommunicationThreadOut)
async def mark_thread_read(
    thread_id: str,
    body: CommunicationMarkReadRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationThreadOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    now = _now_utc()
    stmt = sa.update(CommunicationMessage).where(
        CommunicationMessage.tenant_id == tenant_id,
        CommunicationMessage.thread_id == thread_id,
        CommunicationMessage.direction == "inbound",
        CommunicationMessage.read_at.is_(None),
    )
    if body.message_ids:
        stmt = stmt.where(CommunicationMessage.id.in_([str(x) for x in body.message_ids]))
    stmt = stmt.values(read_at=now, delivery_status=sa.case((CommunicationMessage.delivery_status == "delivered", "read"), else_=CommunicationMessage.delivery_status))
    await db.execute(stmt)
    if body.mark_thread:
        thread.unread_count = 0
        thread.updated_at = now
    await db.commit()
    await db.refresh(thread)
    return _thread_out(thread)


@router.post("/threads/reconcile-unread", response_model=CommunicationUnreadReconcileResponse)
async def reconcile_thread_unread(
    body: CommunicationUnreadReconcileRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationUnreadReconcileResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if body.channel:
        await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(body.channel))
    else:
        await _require_any_comm_feature(db, tenant_id=tenant_id, current_user=current_user, features=["messages", "email"])

    threads_stmt = sa.select(CommunicationThread.id, CommunicationThread.unread_count).where(
        CommunicationThread.tenant_id == tenant_id
    )
    if body.channel:
        threads_stmt = threads_stmt.where(CommunicationThread.channel == body.channel)
    if not body.include_archived:
        threads_stmt = threads_stmt.where(CommunicationThread.is_archived.is_(False))
    threads_stmt = threads_stmt.order_by(
        sa.desc(sa.func.coalesce(CommunicationThread.last_message_at, CommunicationThread.updated_at)),
        sa.desc(CommunicationThread.updated_at),
    ).limit(body.limit)
    thread_rows = (await db.execute(threads_stmt)).all()
    if not thread_rows:
        return CommunicationUnreadReconcileResponse(processed=0, updated=0, total_unread=0)

    thread_ids = [str(row[0]) for row in thread_rows]
    counts_stmt = (
        sa.select(CommunicationMessage.thread_id, sa.func.count())
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.thread_id.in_(thread_ids),
            CommunicationMessage.direction == "inbound",
            CommunicationMessage.read_at.is_(None),
            sa.not_(
                sa.or_(
                    sa.func.coalesce(
                        CommunicationMessage.payload.op("->>")("telegram_command"),
                        "",
                    )
                    == "true",
                    sa.and_(
                        CommunicationMessage.channel == "telegram",
                        CommunicationMessage.body_text.is_not(None),
                        CommunicationMessage.body_text.like("/%"),
                    ),
                )
            ),
        )
        .group_by(CommunicationMessage.thread_id)
    )
    unread_map = {str(thread_id): int(count or 0) for thread_id, count in (await db.execute(counts_stmt)).all()}

    now = _now_utc()
    updated = 0
    total_unread = 0
    for thread_id, current_unread in thread_rows:
        thread_id_str = str(thread_id)
        expected = int(unread_map.get(thread_id_str, 0))
        total_unread += expected
        current = int(current_unread or 0)
        if current == expected:
            continue
        await db.execute(
            sa.update(CommunicationThread)
            .where(
                CommunicationThread.tenant_id == tenant_id,
                CommunicationThread.id == thread_id_str,
            )
            .values(unread_count=expected, updated_at=now)
        )
        updated += 1

    if updated > 0:
        await db.commit()
    return CommunicationUnreadReconcileResponse(processed=len(thread_rows), updated=updated, total_unread=total_unread)


@router.post("/threads/{thread_id}/assign-auto", response_model=CommunicationAutoAssignResponse)
async def auto_assign_thread(
    thread_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAutoAssignResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    result = await allocate_thread(
        db,
        tenant=tenant,
        thread=thread,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
    )
    await db.commit()
    await db.refresh(thread)
    return CommunicationAutoAssignResponse(
        assigned=bool(result.get("assigned")),
        thread=_thread_out(thread),
        reason=result.get("reason"),
        strategy=result.get("strategy"),
        assignee_id=result.get("assignee_id"),
        candidates=result.get("candidates") or [],
    )


@router.post("/allocator/preview", response_model=CommunicationAllocatorPreviewResponse)
async def allocator_preview(
    body: CommunicationAllocatorPreviewRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAllocatorPreviewResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature="communicationsAdmin")
    result = await preview_allocation(
        db,
        tenant=tenant,
        channel=body.channel,
        now_override=body.at,
    )
    return CommunicationAllocatorPreviewResponse(
        assigned=bool(result.get("assigned")),
        reason=result.get("reason"),
        strategy=result.get("strategy"),
        assignee_id=result.get("winner_manager_id"),
        evaluated_at=result.get("evaluated_at"),
        candidates=result.get("candidates") or [],
    )


@router.get("/allocator/audit", response_model=CommunicationAllocationAuditListResponse)
async def list_allocator_audit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    mode: str | None = Query(None),
    channel: str | None = Query(None),
    thread_id: str | None = Query(None),
    assignee_id: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAllocationAuditListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="communicationsAdmin")
    stmt = sa.select(CommunicationAllocationAudit).where(CommunicationAllocationAudit.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationAllocationAudit).where(CommunicationAllocationAudit.tenant_id == tenant_id)
    filters = []
    if mode:
        filters.append(CommunicationAllocationAudit.mode == mode)
    if channel:
        filters.append(CommunicationAllocationAudit.channel == channel)
    if thread_id:
        filters.append(CommunicationAllocationAudit.thread_id == thread_id)
    if assignee_id:
        filters.append(CommunicationAllocationAudit.assignee_id == assignee_id)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    stmt = stmt.order_by(sa.desc(sa.func.coalesce(CommunicationAllocationAudit.evaluated_at, CommunicationAllocationAudit.created_at))).limit(limit).offset(offset)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationAllocationAuditListResponse(items=[_allocation_audit_out(r) for r in rows], total=total)


@router.post("/commands/audit/batch", response_model=CommunicationCommandAuditBatchResponse)
async def create_command_audit_batch(
    body: CommunicationCommandAuditBatchCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationCommandAuditBatchResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(
        tenant=tenant,
        current_user=current_user,
        tenant_id=tenant_id,
        feature=_feature_for_channel(body.channel),
    )  # type: ignore[arg-type]

    requested_ids = [str(x).strip() for x in (body.thread_ids or []) if str(x).strip()]
    unique_ids: list[str] = []
    seen: set[str] = set()
    for tid in requested_ids:
        if tid in seen:
            continue
        seen.add(tid)
        unique_ids.append(tid)
    if not unique_ids:
        return CommunicationCommandAuditBatchResponse(created=0, items=[])

    thread_rows = (
        await db.execute(
            sa.select(CommunicationThread.id, CommunicationThread.channel).where(
                CommunicationThread.tenant_id == tenant_id,
                CommunicationThread.id.in_(unique_ids),
            )
        )
    ).all()
    allowed_thread_ids = [str(r[0]) for r in thread_rows if str(r[1] or "").strip().lower() == str(body.channel or "").strip().lower()]
    if not allowed_thread_ids:
        return CommunicationCommandAuditBatchResponse(created=0, items=[])

    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    executed_at = body.executed_at or _now_utc()
    action_count = len([a for a in (body.actions_json or []) if isinstance(a, dict)])
    created_rows: list[CommunicationCommandAudit] = []
    for thread_id in allowed_thread_ids:
        row = CommunicationCommandAudit(
            tenant_id=tenant_id,
            thread_id=thread_id,
            channel=str(body.channel or "").strip().lower(),
            command_id=body.command_id,
            command_label=body.command_label,
            actor_user_id=actor_id,
            action_count=action_count,
            actions_json=[a for a in (body.actions_json or []) if isinstance(a, dict)],
            payload=_as_dict(body.payload),
            executed_at=executed_at,
        )
        db.add(row)
        created_rows.append(row)
    await db.commit()
    for row in created_rows:
        await db.refresh(row)
    return CommunicationCommandAuditBatchResponse(created=len(created_rows), items=[_command_audit_out(r) for r in created_rows])


@router.get("/commands/audit", response_model=CommunicationCommandAuditListResponse)
async def list_command_audit(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    channel: str | None = Query(None),
    thread_id: str | None = Query(None),
    command_id: str | None = Query(None),
    actor_user_id: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationCommandAuditListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="communicationsAdmin")
    stmt = sa.select(CommunicationCommandAudit).where(CommunicationCommandAudit.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationCommandAudit).where(CommunicationCommandAudit.tenant_id == tenant_id)
    filters = []
    if channel:
        filters.append(CommunicationCommandAudit.channel == str(channel).strip().lower())
    if thread_id:
        filters.append(CommunicationCommandAudit.thread_id == thread_id)
    if command_id:
        filters.append(CommunicationCommandAudit.command_id == command_id)
    if actor_user_id:
        filters.append(CommunicationCommandAudit.actor_user_id == actor_user_id)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    stmt = stmt.order_by(sa.desc(sa.func.coalesce(CommunicationCommandAudit.executed_at, CommunicationCommandAudit.created_at))).limit(limit).offset(offset)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationCommandAuditListResponse(items=[_command_audit_out(r) for r in rows], total=total)


@router.post("/ingest/email", response_model=EmailIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_email(
    body: EmailIngestRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> EmailIngestResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature="email")

    if body.channel_account_id:
        account = await db.get(CommunicationChannelAccount, body.channel_account_id)
        if account is None or str(account.tenant_id) != tenant_id or account.channel != "email":
            raise HTTPException(status_code=404, detail="Email channel account not found")

    # Idempotency by external provider message reference.
    if body.external_message_ref:
        existing_msg_stmt = sa.select(CommunicationMessage).where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.channel == "email",
            CommunicationMessage.external_message_ref == body.external_message_ref,
        ).limit(1)
        existing_msg = (await db.execute(existing_msg_stmt)).scalars().first()
        if existing_msg:
            thread = await _get_thread_or_404(db, tenant_id, str(existing_msg.thread_id))
            return EmailIngestResponse(
                created_thread=False,
                duplicate_message=True,
                auto_assigned=False,
                auto_assign_reason="duplicate_message",
                thread=_thread_out(thread),
                message=_message_out(existing_msg),
            )

    thread = await _find_thread_for_inbound_email(
        db,
        tenant_id=tenant_id,
        channel_account_id=body.channel_account_id,
        provider_thread_ref=body.provider_thread_ref,
        subject=body.subject,
        from_address=body.from_address,
    )
    created_thread = False

    if thread is None:
        participants = {
            "senders": [body.from_address] if body.from_address else [],
            "recipients": [body.to_address] if body.to_address else [],
            "cc": body.cc,
            "bcc": body.bcc,
        }
        thread = CommunicationThread(
            tenant_id=tenant_id,
            channel="email",
            channel_account_id=body.channel_account_id,
            channel_thread_ref=body.provider_thread_ref,
            subject=body.subject,
            status="open",
            direction_hint="inbound",
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            linked_candidate_id=body.linked_candidate_id,
            linked_company_id=body.linked_company_id,
            assignee_id=body.assignee_id,
            owner_id=actor_id,
            queue_assigned_by="manual" if body.assignee_id else None,
            priority="normal",
            participants_json=participants,
            tags_json=[],
            thread_meta={"provider": body.provider} if body.provider else {},
        )
        db.add(thread)
        await db.flush()
        created_thread = True
    else:
        # Refresh some metadata for existing thread
        participants = _as_dict(thread.participants_json)
        senders = participants.get("senders")
        if not isinstance(senders, list):
            senders = []
        if body.from_address and body.from_address not in senders:
            senders.append(body.from_address)
        participants["senders"] = senders
        recipients = participants.get("recipients")
        if not isinstance(recipients, list):
            recipients = []
        if body.to_address and body.to_address not in recipients:
            recipients.append(body.to_address)
        participants["recipients"] = recipients
        if body.cc:
            participants["cc"] = body.cc
        thread.participants_json = participants
        if body.subject and not thread.subject:
            thread.subject = body.subject
        if body.entity_type and not thread.entity_type:
            thread.entity_type = body.entity_type
        if body.entity_id and not thread.entity_id:
            thread.entity_id = body.entity_id
        if body.linked_candidate_id and not thread.linked_candidate_id:
            thread.linked_candidate_id = body.linked_candidate_id
        if body.linked_company_id and not thread.linked_company_id:
            thread.linked_company_id = body.linked_company_id

    received_at = body.received_at or _now_utc()
    msg = CommunicationMessage(
        tenant_id=tenant_id,
        thread_id=str(thread.id),
        channel="email",
        message_type="email",
        direction="inbound",
        sender_type="external",
        sender_label=body.from_name,
        sender_address=body.from_address,
        recipient_type="tenant",
        recipient_label=body.to_name,
        recipient_address=body.to_address,
        subject=body.subject,
        body_text=body.text,
        body_html=body.html,
        attachments_json=[],
        payload={
            **(body.payload or {}),
            "headers": body.headers or {},
            "cc": body.cc,
            "bcc": body.bcc,
            "provider": body.provider,
        },
        external_message_ref=body.external_message_ref,
        delivery_status="delivered",
        sent_at=received_at,
        delivered_at=received_at,
        read_at=None,
        is_internal_note=False,
    )
    db.add(msg)
    await db.flush()
    _touch_thread_from_message(thread, msg, tenant=tenant)

    auto_assigned = False
    auto_assign_reason: str | None = None
    if body.auto_assign and not thread.assignee_id:
        alloc = await allocate_thread(db, tenant=tenant, thread=thread, actor_user_id=actor_id)
        auto_assigned = bool(alloc.get("assigned"))
        auto_assign_reason = None if auto_assigned else str(alloc.get("reason") or "no_eligible_managers")

    await db.commit()
    await db.refresh(thread)
    await db.refresh(msg)
    return EmailIngestResponse(
        created_thread=created_thread,
        duplicate_message=False,
        auto_assigned=auto_assigned,
        auto_assign_reason=auto_assign_reason,
        thread=_thread_out(thread),
        message=_message_out(msg),
    )


@router.post("/ingest/{channel}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_generic_channel(
    channel: str,
    body: GenericInboundIngestRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> GenericInboundIngestResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature="messages")
    channel_norm = (channel or "").strip().lower()
    if channel_norm in {"", "email"}:
        raise HTTPException(status_code=400, detail="Use /communications/ingest/email for email channel")

    if body.channel_account_id:
        account = await db.get(CommunicationChannelAccount, body.channel_account_id)
        if account is None or str(account.tenant_id) != tenant_id or str(account.channel).lower() != channel_norm:
            raise HTTPException(status_code=404, detail="Channel account not found")

    if body.external_message_ref:
        existing_msg_stmt = sa.select(CommunicationMessage).where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.channel == channel_norm,
            CommunicationMessage.external_message_ref == body.external_message_ref,
        ).limit(1)
        existing_msg = (await db.execute(existing_msg_stmt)).scalars().first()
        if existing_msg:
            thread = await _get_thread_or_404(db, tenant_id, str(existing_msg.thread_id))
            return GenericInboundIngestResponse(
                created_thread=False,
                duplicate_message=True,
                auto_assigned=False,
                auto_assign_reason="duplicate_message",
                thread=_thread_out(thread),
                message=_message_out(existing_msg),
            )

    provider_thread_ref = body.provider_thread_ref or body.provider_chat_ref
    thread = await _find_thread_for_inbound_channel(
        db,
        tenant_id=tenant_id,
        channel=channel_norm,
        channel_account_id=body.channel_account_id,
        provider_thread_ref=provider_thread_ref,
        sender_address=body.sender_address,
    )
    created_thread = False
    if thread is None:
        participants = {
            "senders": [body.sender_address] if body.sender_address else [],
            "recipients": [body.recipient_address] if body.recipient_address else [],
        }
        thread = CommunicationThread(
            tenant_id=tenant_id,
            channel=channel_norm,
            channel_account_id=body.channel_account_id,
            channel_thread_ref=provider_thread_ref,
            subject=body.subject,
            status="open",
            direction_hint="inbound",
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            linked_candidate_id=body.linked_candidate_id,
            linked_company_id=body.linked_company_id,
            assignee_id=body.assignee_id,
            owner_id=actor_id,
            queue_assigned_by="manual" if body.assignee_id else None,
            priority="normal",
            participants_json=participants,
            tags_json=[],
            thread_meta={"provider": body.provider} if body.provider else {},
        )
        db.add(thread)
        await db.flush()
        created_thread = True
    else:
        participants = _as_dict(thread.participants_json)
        senders = participants.get("senders")
        if not isinstance(senders, list):
            senders = []
        if body.sender_address and body.sender_address not in senders:
            senders.append(body.sender_address)
        participants["senders"] = senders
        recipients = participants.get("recipients")
        if not isinstance(recipients, list):
            recipients = []
        if body.recipient_address and body.recipient_address not in recipients:
            recipients.append(body.recipient_address)
        participants["recipients"] = recipients
        thread.participants_json = participants
        if body.subject and not thread.subject:
            thread.subject = body.subject
        if provider_thread_ref and not thread.channel_thread_ref:
            thread.channel_thread_ref = provider_thread_ref
        if body.entity_type and not thread.entity_type:
            thread.entity_type = body.entity_type
        if body.entity_id and not thread.entity_id:
            thread.entity_id = body.entity_id
        if body.linked_candidate_id and str(thread.linked_candidate_id or "").strip() != str(body.linked_candidate_id).strip():
            thread.linked_candidate_id = body.linked_candidate_id
        if body.linked_company_id and str(thread.linked_company_id or "").strip() != str(body.linked_company_id).strip():
            thread.linked_company_id = body.linked_company_id

    received_at = body.received_at or _now_utc()
    msg = CommunicationMessage(
        tenant_id=tenant_id,
        thread_id=str(thread.id),
        channel=channel_norm,
        message_type="text" if not body.html else "rich_text",
        direction="inbound",
        sender_type="external",
        sender_label=body.sender_label,
        sender_address=body.sender_address,
        recipient_type="tenant",
        recipient_label=body.recipient_label,
        recipient_address=body.recipient_address,
        subject=body.subject,
        body_text=body.text,
        body_html=body.html,
        attachments_json=body.attachments,
        payload={
            **(body.payload or {}),
            "headers": body.headers or {},
            "provider": body.provider,
            "provider_chat_ref": body.provider_chat_ref,
        },
        external_message_ref=body.external_message_ref,
        delivery_status="delivered",
        sent_at=received_at,
        delivered_at=received_at,
        read_at=received_at
        if channel_norm == "telegram" and bool(_as_dict(body.payload).get("telegram_command"))
        else None,
        is_internal_note=False,
    )
    db.add(msg)
    await db.flush()
    _touch_thread_from_message(thread, msg, tenant=tenant)

    auto_assigned = False
    auto_assign_reason: str | None = None
    if body.auto_assign and not thread.assignee_id:
        alloc = await allocate_thread(db, tenant=tenant, thread=thread, actor_user_id=actor_id)
        auto_assigned = bool(alloc.get("assigned"))
        auto_assign_reason = None if auto_assigned else str(alloc.get("reason") or "no_eligible_managers")

    await db.commit()
    await db.refresh(thread)
    await db.refresh(msg)
    return GenericInboundIngestResponse(
        created_thread=created_thread,
        duplicate_message=False,
        auto_assigned=auto_assigned,
        auto_assign_reason=auto_assign_reason,
        thread=_thread_out(thread),
        message=_message_out(msg),
    )


@router.post("/telegram/webhook-simulate", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def simulate_telegram_webhook(
    body: TelegramWebhookSimulateRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> GenericInboundIngestResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="messages")
    account = await db.get(CommunicationChannelAccount, body.channel_account_id)
    if account is None or str(account.tenant_id) != tenant_id or str(account.channel).lower() != "telegram":
        raise HTTPException(status_code=404, detail="Telegram channel account not found")
    normalized = normalize_telegram_update(body.update)
    if not normalized:
        raise HTTPException(status_code=422, detail="Unsupported Telegram update payload")
    req = GenericInboundIngestRequest(
        channel_account_id=body.channel_account_id,
        provider="telegram_bot",
        provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
        provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
        external_message_ref=str(normalized.get("external_message_ref") or ""),
        sender_address=str(normalized.get("sender_address") or "") or None,
        sender_label=str(normalized.get("sender_label") or "") or None,
        recipient_address=str(normalized.get("recipient_address") or "") or None,
        recipient_label=str(normalized.get("recipient_label") or "") or None,
        subject=None,
        text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
        html=None,
        attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
        payload=_as_dict(normalized.get("payload")),
        headers=_as_dict(normalized.get("headers")),
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        linked_candidate_id=body.linked_candidate_id,
        linked_company_id=body.linked_company_id,
        auto_assign=body.auto_assign,
    )
    return await ingest_generic_channel(
        "telegram",
        req,
        db_tenant=db_tenant,
        current_user=current_user,
    )


@router.post("/public/telegram/{webhook_secret}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def telegram_webhook_public(
    webhook_secret: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> GenericInboundIngestResponse:
    account = await _find_telegram_account_by_webhook_secret(db, webhook_secret=webhook_secret)
    if account is None:
        raise HTTPException(status_code=404, detail="Telegram webhook not found")
    normalized = normalize_telegram_update(payload)
    if not normalized:
        raise HTTPException(status_code=422, detail="Unsupported Telegram update payload")

    tenant_id = str(account.tenant_id)
    try:
        tenant_uuid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid tenant binding for telegram account")

    handled_command, linked_candidate_id = await _process_public_telegram_candidate_command(
        db,
        account=account,
        tenant_id=tenant_id,
        normalized=normalized,
    )

    req = GenericInboundIngestRequest(
        channel_account_id=str(account.id),
        provider="telegram_bot",
        provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
        provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
        external_message_ref=str(normalized.get("external_message_ref") or ""),
        sender_address=str(normalized.get("sender_address") or "") or None,
        sender_label=str(normalized.get("sender_label") or "") or None,
        recipient_address=str(normalized.get("recipient_address") or "") or None,
        recipient_label=str(normalized.get("recipient_label") or "") or None,
        text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
        html=None,
        attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
        payload=_as_dict(normalized.get("payload")),
        headers=_as_dict(normalized.get("headers")),
        linked_candidate_id=linked_candidate_id,
        auto_assign=True,
    )
    if handled_command:
        req.payload = {
            **_as_dict(req.payload),
            "telegram_command": True,
        }
    # Use direct function call to reuse the same ingest pipeline; no user context for public webhook.
    from types import SimpleNamespace

    return await ingest_generic_channel(
        "telegram",
        req,
        db_tenant=(db, tenant_uuid),
        current_user=SimpleNamespace(sub=None, role="superadmin", tenant_id=tenant_id, email="", raw={}),
    )


@router.get("/public/whatsapp/{webhook_secret}", response_model=None)
async def whatsapp_webhook_verify(
    webhook_secret: str,
    mode: str | None = Query(None, alias="hub.mode"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    verify_token: str | None = Query(None, alias="hub.verify_token"),
    db: AsyncSession = Depends(get_db),
)-> PlainTextResponse:
    account = await _find_whatsapp_account_by_webhook_secret(db, webhook_secret=webhook_secret)
    if account is None:
        raise HTTPException(status_code=404, detail="WhatsApp webhook not found")
    settings_json = _as_dict(account.settings_json)
    wa_json = _as_dict(settings_json.get("whatsapp"))
    expected = str(wa_json.get("webhook_verify_token") or "").strip()
    if str(mode or "").strip() == "subscribe" and expected and str(verify_token or "").strip() == expected:
        return PlainTextResponse(content=(challenge or ""))
    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/public/whatsapp/{webhook_secret}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def whatsapp_webhook_public(
    webhook_secret: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> GenericInboundIngestResponse:
    account = await _find_whatsapp_account_by_webhook_secret(db, webhook_secret=webhook_secret)
    if account is None:
        raise HTTPException(status_code=404, detail="WhatsApp webhook not found")

    tenant_id = str(account.tenant_id)
    try:
        tenant_uuid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid tenant binding for whatsapp account")

    normalized_items = normalize_whatsapp_webhook(payload)
    if not normalized_items:
        raise HTTPException(status_code=422, detail="Unsupported WhatsApp webhook payload")

    from types import SimpleNamespace

    last_resp: GenericInboundIngestResponse | None = None
    for normalized in normalized_items:
        provider_recipient = str(normalized.get("recipient_address") or "").strip()
        cfg = _whatsapp_config_from_account_settings(account)
        if cfg is not None and provider_recipient and provider_recipient != cfg.phone_number_id:
            continue
        req = GenericInboundIngestRequest(
            channel_account_id=str(account.id),
            provider="whatsapp_cloud",
            provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
            provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
            external_message_ref=str(normalized.get("external_message_ref") or ""),
            sender_address=str(normalized.get("sender_address") or "") or None,
            sender_label=str(normalized.get("sender_label") or "") or None,
            recipient_address=provider_recipient or None,
            recipient_label=str(normalized.get("recipient_label") or "") or None,
            text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
            html=None,
            attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
            payload=_as_dict(normalized.get("payload")),
            headers=_as_dict(normalized.get("headers")),
            auto_assign=True,
        )
        last_resp = await ingest_generic_channel(
            "whatsapp",
            req,
            db_tenant=(db, tenant_uuid),
            current_user=SimpleNamespace(sub=None, role="superadmin", tenant_id=tenant_id, email="", raw={}),
        )
    if last_resp is None:
        raise HTTPException(status_code=422, detail="No WhatsApp messages to ingest")
    return last_resp


@router.get("/public/messenger/{webhook_secret}", response_model=None)
async def messenger_webhook_verify(
    webhook_secret: str,
    mode: str | None = Query(None, alias="hub.mode"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    verify_token: str | None = Query(None, alias="hub.verify_token"),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    account = await _find_channel_account_by_webhook_secret(
        db,
        channel="messenger",
        config_key="messenger",
        webhook_secret=webhook_secret,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Messenger webhook not found")
    msg_cfg = _as_dict(_as_dict(account.settings_json).get("messenger"))
    expected = str(msg_cfg.get("webhook_verify_token") or "").strip()
    if str(mode or "").strip() == "subscribe" and expected and str(verify_token or "").strip() == expected:
        return PlainTextResponse(content=(challenge or ""))
    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/public/messenger/{webhook_secret}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def messenger_webhook_public(
    webhook_secret: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> GenericInboundIngestResponse:
    account = await _find_channel_account_by_webhook_secret(
        db,
        channel="messenger",
        config_key="messenger",
        webhook_secret=webhook_secret,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Messenger webhook not found")
    tenant_id = str(account.tenant_id)
    try:
        tenant_uuid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid tenant binding for messenger account")

    normalized_items = normalize_meta_webhook(payload, channel="messenger")
    if not normalized_items:
        raise HTTPException(status_code=422, detail="Unsupported Messenger webhook payload")

    from types import SimpleNamespace

    last_resp: GenericInboundIngestResponse | None = None
    for normalized in normalized_items:
        req = GenericInboundIngestRequest(
            channel_account_id=str(account.id),
            provider="facebook_messenger",
            provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
            provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
            external_message_ref=str(normalized.get("external_message_ref") or ""),
            sender_address=str(normalized.get("sender_address") or "") or None,
            sender_label=str(normalized.get("sender_label") or "") or None,
            recipient_address=str(normalized.get("recipient_address") or "") or None,
            recipient_label=str(normalized.get("recipient_label") or "") or None,
            text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
            html=None,
            attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
            payload=_as_dict(normalized.get("payload")),
            headers=_as_dict(normalized.get("headers")),
            auto_assign=True,
        )
        last_resp = await ingest_generic_channel(
            "messenger",
            req,
            db_tenant=(db, tenant_uuid),
            current_user=SimpleNamespace(sub=None, role="superadmin", tenant_id=tenant_id, email="", raw={}),
        )
    if last_resp is None:
        raise HTTPException(status_code=422, detail="No Messenger messages to ingest")
    return last_resp


@router.get("/public/instagram/{webhook_secret}", response_model=None)
async def instagram_webhook_verify(
    webhook_secret: str,
    mode: str | None = Query(None, alias="hub.mode"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    verify_token: str | None = Query(None, alias="hub.verify_token"),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    account = await _find_channel_account_by_webhook_secret(
        db,
        channel="instagram",
        config_key="instagram",
        webhook_secret=webhook_secret,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Instagram webhook not found")
    ig_cfg = _as_dict(_as_dict(account.settings_json).get("instagram"))
    expected = str(ig_cfg.get("webhook_verify_token") or "").strip()
    if str(mode or "").strip() == "subscribe" and expected and str(verify_token or "").strip() == expected:
        return PlainTextResponse(content=(challenge or ""))
    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/public/instagram/{webhook_secret}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def instagram_webhook_public(
    webhook_secret: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> GenericInboundIngestResponse:
    account = await _find_channel_account_by_webhook_secret(
        db,
        channel="instagram",
        config_key="instagram",
        webhook_secret=webhook_secret,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Instagram webhook not found")
    tenant_id = str(account.tenant_id)
    try:
        tenant_uuid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid tenant binding for instagram account")

    normalized_items = normalize_meta_webhook(payload, channel="instagram")
    if not normalized_items:
        raise HTTPException(status_code=422, detail="Unsupported Instagram webhook payload")

    from types import SimpleNamespace

    last_resp: GenericInboundIngestResponse | None = None
    for normalized in normalized_items:
        req = GenericInboundIngestRequest(
            channel_account_id=str(account.id),
            provider="instagram_graph",
            provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
            provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
            external_message_ref=str(normalized.get("external_message_ref") or ""),
            sender_address=str(normalized.get("sender_address") or "") or None,
            sender_label=str(normalized.get("sender_label") or "") or None,
            recipient_address=str(normalized.get("recipient_address") or "") or None,
            recipient_label=str(normalized.get("recipient_label") or "") or None,
            text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
            html=None,
            attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
            payload=_as_dict(normalized.get("payload")),
            headers=_as_dict(normalized.get("headers")),
            auto_assign=True,
        )
        last_resp = await ingest_generic_channel(
            "instagram",
            req,
            db_tenant=(db, tenant_uuid),
            current_user=SimpleNamespace(sub=None, role="superadmin", tenant_id=tenant_id, email="", raw={}),
        )
    if last_resp is None:
        raise HTTPException(status_code=422, detail="No Instagram messages to ingest")
    return last_resp


@router.post("/public/viber/{webhook_secret}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def viber_webhook_public(
    webhook_secret: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> GenericInboundIngestResponse:
    account = await _find_channel_account_by_webhook_secret(
        db,
        channel="viber",
        config_key="viber",
        webhook_secret=webhook_secret,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Viber webhook not found")
    tenant_id = str(account.tenant_id)
    try:
        tenant_uuid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid tenant binding for viber account")

    normalized = normalize_viber_webhook(payload)
    if not normalized:
        raise HTTPException(status_code=422, detail="Unsupported Viber webhook payload")

    from types import SimpleNamespace

    req = GenericInboundIngestRequest(
        channel_account_id=str(account.id),
        provider="viber_bot",
        provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
        provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
        external_message_ref=str(normalized.get("external_message_ref") or ""),
        sender_address=str(normalized.get("sender_address") or "") or None,
        sender_label=str(normalized.get("sender_label") or "") or None,
        recipient_address=str(normalized.get("recipient_address") or "") or None,
        recipient_label=str(normalized.get("recipient_label") or "") or None,
        text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
        html=None,
        attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
        payload=_as_dict(normalized.get("payload")),
        headers=_as_dict(normalized.get("headers")),
        auto_assign=True,
    )
    return await ingest_generic_channel(
        "viber",
        req,
        db_tenant=(db, tenant_uuid),
        current_user=SimpleNamespace(sub=None, role="superadmin", tenant_id=tenant_id, email="", raw={}),
    )


@router.get(
    "/time-off/requests",
    response_model=TimeOffRequestListResponse,
    dependencies=[
        Depends(
            require_roles(
                Role.administrator,
                Role.supervisor,
                Role.recruiter,
                Role.client_manager,
                Role.client_processor,
            )
        )
    ],
)
async def list_time_off_requests(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    mine_only: bool = Query(False),
    status_filter: List[str] | None = Query(None),
    requester_user_id: str | None = Query(None),
    approver_user_id: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> TimeOffRequestListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "timeOffRequests"],
    )
    stmt = sa.select(CommunicationTimeOffRequest).where(CommunicationTimeOffRequest.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationTimeOffRequest).where(CommunicationTimeOffRequest.tenant_id == tenant_id)

    filters = []
    if mine_only:
        filters.append(CommunicationTimeOffRequest.requester_user_id == str(current_user.sub))
    if requester_user_id:
        filters.append(CommunicationTimeOffRequest.requester_user_id == requester_user_id)
    if approver_user_id:
        filters.append(CommunicationTimeOffRequest.approver_user_id == approver_user_id)
    if status_filter:
        filters.append(CommunicationTimeOffRequest.status.in_([str(x) for x in status_filter]))
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    stmt = stmt.order_by(sa.desc(sa.func.coalesce(CommunicationTimeOffRequest.requested_at, CommunicationTimeOffRequest.created_at))).limit(limit).offset(offset)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return TimeOffRequestListResponse(items=[_timeoff_out(r) for r in rows], total=total)


@router.get(
    "/availability/working-hours",
    response_model=WorkingHoursScheduleOut,
    dependencies=[
        Depends(
            require_roles(
                Role.administrator,
                Role.supervisor,
                Role.recruiter,
                Role.client_manager,
                Role.client_processor,
            )
        )
    ],
)
async def get_my_working_hours(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> WorkingHoursScheduleOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "planner", "calendar", "teamAvailability"],
    )
    user = await db.get(User, str(current_user.sub))
    if user is None or str(user.tenant_id or "") != tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    extra = user.extra if isinstance(user.extra, dict) else {}
    payload = extra.get("working_hours_v1") if isinstance(extra, dict) else None
    normalized = _normalize_working_hours(payload)
    return WorkingHoursScheduleOut(tz=normalized.get("tz"), days=normalized.get("days") or [])


@router.put(
    "/availability/working-hours",
    response_model=WorkingHoursScheduleOut,
    dependencies=[
        Depends(
            require_roles(
                Role.administrator,
                Role.supervisor,
                Role.recruiter,
                Role.client_manager,
                Role.client_processor,
            )
        )
    ],
)
async def upsert_my_working_hours(
    body: WorkingHoursScheduleIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> WorkingHoursScheduleOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "planner", "calendar", "teamAvailability"],
    )
    user = await db.get(User, str(current_user.sub))
    if user is None or str(user.tenant_id or "") != tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    normalized = _normalize_working_hours(body.model_dump(by_alias=True))
    extra = user.extra if isinstance(user.extra, dict) else {}
    extra = {**extra, "working_hours_v1": normalized}
    user.extra = extra
    await db.commit()
    return WorkingHoursScheduleOut(tz=normalized.get("tz"), days=normalized.get("days") or [])


@router.post(
    "/time-off/requests",
    response_model=TimeOffRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            require_roles(
                Role.administrator,
                Role.supervisor,
                Role.recruiter,
                Role.client_manager,
                Role.client_processor,
            )
        )
    ],
)
async def create_time_off_request(
    body: TimeOffRequestCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> TimeOffRequestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "timeOffRequests"],
    )
    _validate_iso_date_range(body.start_date, body.end_date)
    now = _now_utc()
    req = CommunicationTimeOffRequest(
        tenant_id=tenant_id,
        requester_user_id=str(current_user.sub),
        requester_label=(getattr(current_user, "email", None) or str(current_user.sub)),
        approver_user_id=body.approver_user_id or current_user.supervisor_id,
        approver_label=body.approver_label,
        request_type=(body.request_type or "vacation").strip().lower(),
        status="pending",
        start_date=body.start_date.strip(),
        end_date=body.end_date.strip(),
        partial_day=(body.partial_day or "").strip() or None,
        reason=body.reason,
        requested_at=now,
        payload=_as_dict(body.payload),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return _timeoff_out(req)


@router.post(
    "/time-off/requests/{request_id}/cancel",
    response_model=TimeOffRequestOut,
    dependencies=[
        Depends(
            require_roles(
                Role.administrator,
                Role.supervisor,
                Role.recruiter,
                Role.client_manager,
                Role.client_processor,
            )
        )
    ],
)
async def cancel_time_off_request(
    request_id: str,
    body: TimeOffRequestCancel,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> TimeOffRequestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "timeOffRequests"],
    )
    row = await db.get(CommunicationTimeOffRequest, request_id)
    if row is None or str(row.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Time-off request not found")
    is_admin_like = (current_user.role or "").strip().lower() in {Role.administrator.value, Role.supervisor.value, Role.superadmin.value}
    if str(row.requester_user_id) != str(current_user.sub) and not is_admin_like:
        raise HTTPException(status_code=403, detail="Forbidden")
    if str(row.status or "").lower() not in {"pending"}:
        raise HTTPException(status_code=409, detail="Only pending request can be cancelled")
    row.status = "cancelled"
    row.decision_note = body.reason or row.decision_note
    row.decided_at = _now_utc()
    row.updated_at = _now_utc()
    await db.commit()
    await db.refresh(row)
    return _timeoff_out(row)


@router.post(
    "/time-off/requests/{request_id}/decision",
    response_model=TimeOffRequestOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def decide_time_off_request(
    request_id: str,
    body: TimeOffRequestDecision,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> TimeOffRequestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature="timeOffRequests")
    row = await db.get(CommunicationTimeOffRequest, request_id)
    if row is None or str(row.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Time-off request not found")
    if str(row.status or "").lower() not in {"pending"}:
        raise HTTPException(status_code=409, detail="Only pending request can be decided")
    row.status = body.decision
    row.decision_note = body.decision_note
    row.approver_user_id = str(current_user.sub)
    row.approver_label = getattr(current_user, "email", None) or row.approver_label
    row.decided_at = _now_utc()
    row.updated_at = _now_utc()
    try:
        await _sync_manager_queue_availability_from_time_off(
            db,
            tenant=tenant,
            user_id=str(row.requester_user_id),
            now_utc=row.updated_at or _now_utc(),
        )
    except Exception as e:
        logger.warning("[communications:timeoff] availability sync skipped request=%s (%s)", request_id, e)
    await db.commit()
    await db.refresh(row)
    return _timeoff_out(row)


@router.get("/planner/events", response_model=CommunicationPlannerEventListResponse)
async def list_planner_events(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: List[str] | None = Query(None),
    assignee_id: str | None = Query(None),
    from_at: datetime | None = Query(None),
    to_at: datetime | None = Query(None),
    kind: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationPlannerEventListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="planner")
    stmt = sa.select(CommunicationPlannerEvent).where(CommunicationPlannerEvent.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationPlannerEvent).where(CommunicationPlannerEvent.tenant_id == tenant_id)
    filters = []
    if status_filter:
        filters.append(CommunicationPlannerEvent.status.in_([str(x) for x in status_filter]))
    if assignee_id:
        filters.append(CommunicationPlannerEvent.assignee_id == assignee_id)
    if kind:
        filters.append(CommunicationPlannerEvent.kind == kind)
    if from_at:
        filters.append(sa.func.coalesce(CommunicationPlannerEvent.end_at, CommunicationPlannerEvent.start_at) >= from_at)
    if to_at:
        filters.append(CommunicationPlannerEvent.start_at <= to_at)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    stmt = stmt.order_by(sa.asc(CommunicationPlannerEvent.start_at), sa.asc(CommunicationPlannerEvent.created_at)).limit(limit).offset(offset)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationPlannerEventListResponse(items=[_planner_event_out(r) for r in rows], total=total)


@router.post("/planner/events", response_model=CommunicationPlannerEventOut, status_code=status.HTTP_201_CREATED)
async def create_planner_event(
    body: CommunicationPlannerEventCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationPlannerEventOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="planner")
    if body.end_at and body.end_at < body.start_at:
        raise HTTPException(status_code=422, detail="end_at must be greater than or equal to start_at")
    row = CommunicationPlannerEvent(
        tenant_id=tenant_id,
        title=body.title.strip(),
        description=body.description,
        kind=(body.kind or "task").strip().lower(),
        status=(body.status or "planned").strip().lower(),
        priority=(body.priority or "normal").strip().lower(),
        start_at=body.start_at if body.start_at.tzinfo else body.start_at.replace(tzinfo=timezone.utc),
        end_at=(body.end_at if (body.end_at and body.end_at.tzinfo) else (body.end_at.replace(tzinfo=timezone.utc) if body.end_at else None)),
        all_day=bool(body.all_day),
        owner_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        assignee_id=body.assignee_id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        linked_candidate_id=body.linked_candidate_id,
        linked_company_id=body.linked_company_id,
        source=(body.source or "manual").strip().lower(),
        payload=_as_dict(body.payload),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _planner_event_out(row)


@router.patch("/planner/events/{event_id}", response_model=CommunicationPlannerEventOut)
async def patch_planner_event(
    event_id: str,
    body: CommunicationPlannerEventPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationPlannerEventOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="planner")
    row = await db.get(CommunicationPlannerEvent, event_id)
    if row is None or str(row.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Planner event not found")

    patch = body.model_dump(exclude_unset=True)
    for key in ["title", "description", "kind", "status", "priority", "all_day", "assignee_id", "entity_type", "entity_id", "linked_candidate_id", "linked_company_id"]:
        if key in patch:
            value = patch[key]
            if key in {"kind", "status", "priority"} and isinstance(value, str):
                value = value.strip().lower()
            if key == "title" and isinstance(value, str):
                value = value.strip()
            setattr(row, key, value)
    if "start_at" in patch:
        dt = patch["start_at"]
        row.start_at = dt if (dt is None or dt.tzinfo) else dt.replace(tzinfo=timezone.utc)
    if "end_at" in patch:
        dt = patch["end_at"]
        row.end_at = dt if (dt is None or dt.tzinfo) else dt.replace(tzinfo=timezone.utc)
    if row.end_at and row.end_at < row.start_at:
        raise HTTPException(status_code=422, detail="end_at must be greater than or equal to start_at")
    if "payload" in patch and patch["payload"] is not None:
        row.payload = _as_dict(patch["payload"])
    row.updated_at = _now_utc()
    await db.commit()
    await db.refresh(row)
    return _planner_event_out(row)


@router.get("/accounts", response_model=CommunicationChannelAccountListResponse)
async def list_channel_accounts(
    channel: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationChannelAccountListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if channel:
        await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(channel))
    else:
        await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="communicationsAdmin")
    stmt = sa.select(CommunicationChannelAccount).where(CommunicationChannelAccount.tenant_id == tenant_id)
    if channel:
        stmt = stmt.where(CommunicationChannelAccount.channel == channel)
    stmt = stmt.order_by(sa.asc(CommunicationChannelAccount.channel), sa.asc(CommunicationChannelAccount.account_label))
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationChannelAccountListResponse(
        items=[_account_out(a) for a in rows]
    )


@router.post("/accounts", response_model=CommunicationChannelAccountOut, status_code=status.HTTP_201_CREATED)
async def create_channel_account(
    body: CommunicationChannelAccountCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationChannelAccountOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(body.channel))
    normalized_settings = _normalize_account_settings_for_store(body.settings_json)
    if str(body.channel).lower() == "telegram":
        settings = _as_dict(normalized_settings)
        tg = _as_dict(settings.get("telegram"))
        if not str(tg.get("webhook_secret") or "").strip():
            tg["webhook_secret"] = generate_secret(48)
        settings["telegram"] = tg
        normalized_settings = settings
    if str(body.channel).lower() == "whatsapp":
        settings = _as_dict(normalized_settings)
        wa = _as_dict(settings.get("whatsapp"))
        if not str(wa.get("webhook_secret") or "").strip():
            wa["webhook_secret"] = generate_secret(48)
        if not str(wa.get("webhook_verify_token") or "").strip():
            wa["webhook_verify_token"] = generate_secret(24)
        settings["whatsapp"] = wa
        normalized_settings = settings
    if str(body.channel).lower() == "messenger":
        settings = _as_dict(normalized_settings)
        msg = _as_dict(settings.get("messenger"))
        if not str(msg.get("webhook_secret") or "").strip():
            msg["webhook_secret"] = generate_secret(48)
        if not str(msg.get("webhook_verify_token") or "").strip():
            msg["webhook_verify_token"] = generate_secret(24)
        settings["messenger"] = msg
        normalized_settings = settings
    if str(body.channel).lower() == "instagram":
        settings = _as_dict(normalized_settings)
        ig = _as_dict(settings.get("instagram"))
        if not str(ig.get("webhook_secret") or "").strip():
            ig["webhook_secret"] = generate_secret(48)
        if not str(ig.get("webhook_verify_token") or "").strip():
            ig["webhook_verify_token"] = generate_secret(24)
        settings["instagram"] = ig
        normalized_settings = settings
    if str(body.channel).lower() == "viber":
        settings = _as_dict(normalized_settings)
        viber = _as_dict(settings.get("viber"))
        if not str(viber.get("webhook_secret") or "").strip():
            viber["webhook_secret"] = generate_secret(48)
        settings["viber"] = viber
        normalized_settings = settings

    account = CommunicationChannelAccount(
        tenant_id=tenant_id,
        channel=body.channel,
        account_label=body.account_label,
        external_account_ref=body.external_account_ref,
        inbox_address=body.inbox_address,
        is_active=body.is_active,
        settings_json=normalized_settings,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return _account_out(account)


@router.patch("/accounts/{account_id}", response_model=CommunicationChannelAccountOut)
async def patch_channel_account(
    account_id: str,
    body: CommunicationChannelAccountPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationChannelAccountOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    patch = body.model_dump(exclude_unset=True)
    if "account_label" in patch and patch["account_label"] is not None:
        account.account_label = str(patch["account_label"]).strip()
    if "external_account_ref" in patch:
        account.external_account_ref = patch["external_account_ref"]
    if "inbox_address" in patch:
        account.inbox_address = patch["inbox_address"]
    if "is_active" in patch and patch["is_active"] is not None:
        account.is_active = bool(patch["is_active"])
    if "settings_json" in patch and patch["settings_json"] is not None:
        merged = _deep_merge_dict(_as_dict(account.settings_json), _as_dict(patch["settings_json"]))
        account.settings_json = _normalize_account_settings_for_store(merged)

    await db.commit()
    await db.refresh(account)
    return _account_out(account)


@router.post("/accounts/{account_id}/test-connection", response_model=CommunicationAccountActionResponse)
async def test_channel_account_connection(
    account_id: str,
    request: Request,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountActionResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]
    now = _now_utc()
    account_settings = _as_dict(account.settings_json)
    connection = _as_dict(account_settings.get("connection"))
    provider = str(account_settings.get("provider") or "").strip().lower()
    if account.is_active and provider == "imap":
        try:
            imap_cfg = _imap_config_from_account_settings(account)
            if imap_cfg is None:
                raise RuntimeError("IMAP settings are incomplete (host/user/password)")
            test_result = await test_imap_connection(imap_cfg)
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": test_result,
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and str(account.channel).lower() == "telegram":
        try:
            tg_cfg = _telegram_config_from_account_settings(account)
            if tg_cfg is None:
                raise RuntimeError("Telegram settings are incomplete (bot token is required)")
            me_result = await telegram_get_me(tg_cfg)
            bot_meta = _as_dict(me_result.get("result"))
            tg_settings = _as_dict(account_settings.get("telegram"))
            webhook_secret = str(tg_settings.get("webhook_secret") or "").strip()
            webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
            if webhook_base.endswith("/app"):
                webhook_base = webhook_base[:-4]
            webhook_url = f"{webhook_base}/api/v1/communications/public/telegram/{webhook_secret}" if webhook_secret else None
            webhook_info = None
            if webhook_url:
                await telegram_set_webhook(tg_cfg, webhook_url=webhook_url)
                webhook_info_result = await telegram_get_webhook_info(tg_cfg)
                webhook_info = _as_dict(webhook_info_result.get("result"))
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": {
                        "method": "getMe",
                        "id": bot_meta.get("id"),
                        "username": bot_meta.get("username"),
                        "first_name": bot_meta.get("first_name"),
                        "can_join_groups": bot_meta.get("can_join_groups"),
                        "can_read_all_group_messages": bot_meta.get("can_read_all_group_messages"),
                        "supports_inline_queries": bot_meta.get("supports_inline_queries"),
                        "webhook_url": webhook_url,
                        "webhook_info": {
                            "url": webhook_info.get("url") if isinstance(webhook_info, dict) else None,
                            "has_custom_certificate": webhook_info.get("has_custom_certificate") if isinstance(webhook_info, dict) else None,
                            "pending_update_count": webhook_info.get("pending_update_count") if isinstance(webhook_info, dict) else None,
                            "last_error_date": webhook_info.get("last_error_date") if isinstance(webhook_info, dict) else None,
                            "last_error_message": webhook_info.get("last_error_message") if isinstance(webhook_info, dict) else None,
                            "ip_address": webhook_info.get("ip_address") if isinstance(webhook_info, dict) else None,
                        } if webhook_info is not None else None,
                    },
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and str(account.channel).lower() == "whatsapp":
        try:
            wa_cfg = _whatsapp_config_from_account_settings(account)
            if wa_cfg is None:
                raise RuntimeError("WhatsApp settings are incomplete (phone_number_id/access_token)")
            info_result = await whatsapp_get_phone_number_info(wa_cfg)
            info = _as_dict(info_result)
            wa_settings = _as_dict(account_settings.get("whatsapp"))
            webhook_secret = str(wa_settings.get("webhook_secret") or "").strip()
            verify_token = str(wa_settings.get("webhook_verify_token") or "").strip()
            webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
            if webhook_base.endswith("/app"):
                webhook_base = webhook_base[:-4]
            webhook_url = f"{webhook_base}/api/v1/communications/public/whatsapp/{webhook_secret}" if webhook_secret else None
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": {
                        "method": "phone_number_info",
                        "id": info.get("id"),
                        "display_phone_number": info.get("display_phone_number"),
                        "verified_name": info.get("verified_name"),
                        "quality_rating": info.get("quality_rating"),
                        "webhook_url": webhook_url,
                        "webhook_verify_token": verify_token,
                    },
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and str(account.channel).lower() == "messenger":
        try:
            meta_cfg, page_id = _messenger_graph_config_from_account_settings(account)
            if meta_cfg is None or not page_id:
                raise RuntimeError("Messenger settings are incomplete (page_id/access_token)")
            info = await meta_graph_get_object(meta_cfg, object_id=page_id, fields="id,name")
            msg_settings = _as_dict(account_settings.get("messenger"))
            webhook_secret = str(msg_settings.get("webhook_secret") or "").strip()
            verify_token = str(msg_settings.get("webhook_verify_token") or "").strip()
            webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
            if webhook_base.endswith("/app"):
                webhook_base = webhook_base[:-4]
            webhook_url = f"{webhook_base}/api/v1/communications/public/messenger/{webhook_secret}" if webhook_secret else None
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": {
                        "method": "meta_page_info",
                        "id": info.get("id"),
                        "name": info.get("name"),
                        "webhook_url": webhook_url,
                        "webhook_verify_token": verify_token,
                    },
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and str(account.channel).lower() == "instagram":
        try:
            meta_cfg, account_id = _instagram_graph_config_from_account_settings(account)
            if meta_cfg is None or not account_id:
                raise RuntimeError("Instagram settings are incomplete (account_id/access_token)")
            info = await meta_graph_get_object(meta_cfg, object_id=account_id, fields="id,username,name")
            ig_settings = _as_dict(account_settings.get("instagram"))
            webhook_secret = str(ig_settings.get("webhook_secret") or "").strip()
            verify_token = str(ig_settings.get("webhook_verify_token") or "").strip()
            webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
            if webhook_base.endswith("/app"):
                webhook_base = webhook_base[:-4]
            webhook_url = f"{webhook_base}/api/v1/communications/public/instagram/{webhook_secret}" if webhook_secret else None
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": {
                        "method": "instagram_account_info",
                        "id": info.get("id"),
                        "username": info.get("username"),
                        "name": info.get("name"),
                        "webhook_url": webhook_url,
                        "webhook_verify_token": verify_token,
                    },
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and str(account.channel).lower() == "viber":
        try:
            viber_cfg = _viber_config_from_account_settings(account)
            if viber_cfg is None:
                raise RuntimeError("Viber settings are incomplete (bot token)")
            info = await viber_get_account_info(viber_cfg)
            viber_settings = _as_dict(account_settings.get("viber"))
            webhook_secret = str(viber_settings.get("webhook_secret") or "").strip()
            webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
            if webhook_base.endswith("/app"):
                webhook_base = webhook_base[:-4]
            webhook_url = f"{webhook_base}/api/v1/communications/public/viber/{webhook_secret}" if webhook_secret else None
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": {
                        "method": "get_account_info",
                        "name": info.get("name"),
                        "id": info.get("id"),
                        "webhook_url": webhook_url,
                    },
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and provider in {"gmail", "microsoft_graph"}:
        oauth = _as_dict(account_settings.get("oauth"))
        has_access_token = bool(_oauth_access_token(oauth))
        has_refresh_token = bool(_oauth_refresh_token(oauth))
        has_client_id = bool(str(oauth.get("client_id") or "").strip())
        oauth_error = None
        if not has_access_token and not has_refresh_token:
            oauth_error = "OAuth is incomplete: access_token or refresh_token is required"
        elif has_refresh_token and not has_client_id:
            oauth_error = "OAuth is incomplete: client_id is required when refresh_token is used"
        connection.update(
            {
                "status": "ok" if oauth_error is None else "error",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": oauth_error,
                "provider_result": {
                    "provider": provider,
                    "has_access_token": has_access_token,
                    "has_refresh_token": has_refresh_token,
                    "has_client_id": has_client_id,
                },
            }
        )
    else:
        connection.update(
            {
                "status": "ok" if account.is_active else "disabled",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": None if account.is_active else "Account disabled",
            }
        )
    account_settings["connection"] = connection
    account.settings_json = account_settings
    await db.commit()
    await db.refresh(account)
    status_value, detail = _derive_account_status(account)
    return CommunicationAccountActionResponse(
        ok=status_value in {"connected", "disabled"},
        action="test_connection",
        status=status_value,
        detail=detail,
        account=_account_out(account),
    )


@router.post("/accounts/{account_id}/telegram/webhook/set", response_model=CommunicationAccountActionResponse)
async def set_telegram_channel_account_webhook(
    account_id: str,
    request: Request,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountActionResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    if str(account.channel).lower() != "telegram":
        raise HTTPException(status_code=422, detail="Webhook management is supported only for Telegram accounts")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    now = _now_utc()
    account_settings = _as_dict(account.settings_json)
    connection = _as_dict(account_settings.get("connection"))
    tg_settings = _as_dict(account_settings.get("telegram"))
    webhook_secret = str(tg_settings.get("webhook_secret") or "").strip()
    if not webhook_secret:
        webhook_secret = generate_secret(48)
        tg_settings["webhook_secret"] = webhook_secret
    webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
    if webhook_base.endswith("/app"):
        webhook_base = webhook_base[:-4]
    webhook_url = f"{webhook_base}/api/v1/communications/public/telegram/{webhook_secret}"

    try:
        tg_cfg = _telegram_config_from_account_settings(account)
        if tg_cfg is None:
            raise RuntimeError("Telegram settings are incomplete (bot token is required)")
        await telegram_set_webhook(tg_cfg, webhook_url=webhook_url)
        webhook_info_result = await telegram_get_webhook_info(tg_cfg)
        webhook_info = _as_dict(webhook_info_result.get("result"))
        connection.update(
            {
                "status": "ok",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": None,
                "provider_result": {
                    "method": "setWebhook",
                    "webhook_url": webhook_url,
                    "webhook_info": webhook_info,
                },
            }
        )
    except Exception as exc:
        connection.update(
            {
                "status": "error",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": str(exc),
            }
        )
        account_settings["telegram"] = tg_settings
        account_settings["connection"] = connection
        account.settings_json = account_settings
        await db.commit()
        await db.refresh(account)
        raise HTTPException(status_code=400, detail=f"Failed to set Telegram webhook: {exc}")

    account_settings["telegram"] = tg_settings
    account_settings["connection"] = connection
    account.settings_json = account_settings
    await db.commit()
    await db.refresh(account)
    status_value, detail = _derive_account_status(account)
    return CommunicationAccountActionResponse(
        ok=status_value in {"connected", "disabled"},
        action="telegram_webhook_set",
        status=status_value,
        detail=detail,
        account=_account_out(account),
    )


@router.post("/accounts/{account_id}/telegram/webhook/delete", response_model=CommunicationAccountActionResponse)
async def delete_telegram_channel_account_webhook(
    account_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountActionResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    if str(account.channel).lower() != "telegram":
        raise HTTPException(status_code=422, detail="Webhook management is supported only for Telegram accounts")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    now = _now_utc()
    account_settings = _as_dict(account.settings_json)
    connection = _as_dict(account_settings.get("connection"))

    try:
        tg_cfg = _telegram_config_from_account_settings(account)
        if tg_cfg is None:
            raise RuntimeError("Telegram settings are incomplete (bot token is required)")
        await telegram_delete_webhook(tg_cfg)
        webhook_info_result = await telegram_get_webhook_info(tg_cfg)
        webhook_info = _as_dict(webhook_info_result.get("result"))
        connection.update(
            {
                "status": "ok",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": None,
                "provider_result": {
                    "method": "deleteWebhook",
                    "webhook_url": webhook_info.get("url"),
                    "webhook_info": webhook_info,
                },
            }
        )
    except Exception as exc:
        connection.update(
            {
                "status": "error",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": str(exc),
            }
        )
        account_settings["connection"] = connection
        account.settings_json = account_settings
        await db.commit()
        await db.refresh(account)
        raise HTTPException(status_code=400, detail=f"Failed to delete Telegram webhook: {exc}")

    account_settings["connection"] = connection
    account.settings_json = account_settings
    await db.commit()
    await db.refresh(account)
    status_value, detail = _derive_account_status(account)
    return CommunicationAccountActionResponse(
        ok=status_value in {"connected", "disabled"},
        action="telegram_webhook_delete",
        status=status_value,
        detail=detail,
        account=_account_out(account),
    )


@router.post("/accounts/{account_id}/sync-now", response_model=CommunicationAccountActionResponse)
async def sync_channel_account_now(
    account_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountActionResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]
    now = _now_utc()
    settings = _as_dict(account.settings_json)
    sync = _as_dict(settings.get("sync"))
    sync.update(
        {
            "status": "ok" if account.is_active else "error",
            "last_sync_at": now.isoformat(),
            "last_sync_by": actor_id,
            "last_error": None if account.is_active else "Account disabled",
            "mode": "manual_trigger",
        }
    )
    settings["sync"] = sync
    account.settings_json = settings
    await db.commit()
    await db.refresh(account)
    status_value, detail = _derive_account_status(account)
    return CommunicationAccountActionResponse(
        ok=bool(account.is_active),
        action="sync_now",
        status=status_value,
        detail=detail,
        account=_account_out(account),
    )


@router.post("/accounts/{account_id}/oauth/start", response_model=CommunicationAccountOAuthStartResponse)
async def start_channel_account_oauth(
    account_id: str,
    body: CommunicationAccountOAuthStartRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountOAuthStartResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    provider = _oauth_provider_for_account(account)
    if provider not in {"gmail", "microsoft_graph"}:
        raise HTTPException(status_code=422, detail=f"OAuth is not supported for provider: {provider}")

    settings = _as_dict(account.settings_json)
    oauth_json = _as_dict(settings.get("oauth"))
    state = generate_secret(40)
    scopes = [s for s in (body.scopes or []) if isinstance(s, str) and s.strip()] or _oauth_default_scopes(provider)
    redirect_uri = (body.redirect_uri or str(oauth_json.get("redirect_uri") or "").strip() or None)
    client_id = str(oauth_json.get("client_id") or "").strip() or None
    if not client_id:
        raise HTTPException(status_code=422, detail="OAuth client_id is not configured")
    if not redirect_uri:
        raise HTTPException(status_code=422, detail="OAuth redirect_uri is not configured")

    oauth_json.update(
        {
            "provider": provider,
            "state": state,
            "state_created_at": _now_utc().isoformat(),
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "oauth_status": "pending",
            "last_error": None,
        }
    )
    settings["oauth"] = oauth_json
    account.settings_json = settings
    await db.commit()
    await db.refresh(account)

    auth_url = _build_oauth_auth_url(
        provider=provider,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
        state=state,
        force_consent=bool(body.force_consent),
    )
    return CommunicationAccountOAuthStartResponse(
        ok=True,
        action="oauth_start",
        provider=provider,
        state=state,
        auth_url=auth_url,
        account=_account_out(account),
    )


@router.post("/accounts/{account_id}/oauth/complete", response_model=CommunicationAccountOAuthCompleteResponse)
async def complete_channel_account_oauth(
    account_id: str,
    body: CommunicationAccountOAuthCompleteRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountOAuthCompleteResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    provider = _oauth_provider_for_account(account)
    settings = _as_dict(account.settings_json)
    oauth_json = _as_dict(settings.get("oauth"))
    expected_state = str(oauth_json.get("state") or "").strip()
    if expected_state and body.state != expected_state:
        raise HTTPException(status_code=409, detail="OAuth state mismatch")

    now = _now_utc()
    access_token = body.access_token
    refresh_token = body.refresh_token
    id_token = body.id_token

    if body.simulate_exchange and not access_token:
        # Foundation mode: allow callback completion without external token exchange.
        # Real adapters (Gmail/Graph) will exchange code and pass real tokens.
        if not (body.code or "").strip():
            raise HTTPException(status_code=422, detail="OAuth code is required")
        access_token = f"sim_{provider}_access_{generate_secret(24)}"
        refresh_token = refresh_token or f"sim_{provider}_refresh_{generate_secret(24)}"
        id_token = id_token or f"sim_{provider}_id_{generate_secret(24)}"
    elif not access_token:
        code = str(body.code or "").strip()
        if not code:
            raise HTTPException(status_code=422, detail="OAuth code is required")
        redirect_uri = str(body.redirect_uri or oauth_json.get("redirect_uri") or "").strip()
        client_id = str(oauth_json.get("client_id") or "").strip()
        client_secret = _oauth_client_secret(oauth_json)
        if not redirect_uri:
            raise HTTPException(status_code=422, detail="OAuth redirect_uri is required")
        if not client_id:
            raise HTTPException(status_code=422, detail="OAuth client_id is required")
        try:
            token_payload = await exchange_oauth_code_for_tokens(
                provider=provider,
                code=code,
                redirect_uri=redirect_uri,
                client_id=client_id,
                client_secret=client_secret,
                code_verifier=body.code_verifier,
            )
        except OAuthProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        access_token = token_payload.access_token
        refresh_token = refresh_token or token_payload.refresh_token
        id_token = id_token or token_payload.id_token
        if not body.scope and token_payload.scope:
            body.scope = token_payload.scope
        if not body.token_type and token_payload.token_type:
            body.token_type = token_payload.token_type
        if token_payload.expires_in:
            body.expires_in = token_payload.expires_in
        if token_payload.provider_payload:
            body.provider_payload = {**token_payload.provider_payload, **_as_dict(body.provider_payload)}

    if not str(access_token or "").strip():
        raise HTTPException(status_code=422, detail="OAuth access token is required")

    oauth_mut = {
        **oauth_json,
        "provider": provider,
        "token_type": body.token_type or "Bearer",
        "scope": body.scope or " ".join(_as_list(oauth_json.get("scopes"))),
        "connected_at": now.isoformat(),
        "oauth_status": "connected",
        "last_error": None,
        "expires_at": (now + timedelta(seconds=int(body.expires_in or 3600))).isoformat(),
        "last_completed_by": str(getattr(current_user, "sub", "") or ""),
        "provider_payload": _as_dict(body.provider_payload),
    }
    oauth_mut["access_token"] = str(access_token)
    if refresh_token:
        oauth_mut["refresh_token"] = str(refresh_token)
    if id_token:
        oauth_mut["id_token"] = str(id_token)

    settings["oauth"] = _normalize_account_settings_for_store({"oauth": oauth_mut}).get("oauth", oauth_mut)
    account.settings_json = settings
    await db.commit()
    await db.refresh(account)

    return CommunicationAccountOAuthCompleteResponse(
        ok=True,
        action="oauth_complete",
        provider=provider,
        account=_account_out(account),
        detail="OAuth mailbox connected",
    )


@router.post("/accounts/{account_id}/oauth/refresh", response_model=CommunicationAccountOAuthCompleteResponse)
async def refresh_channel_account_oauth_token(
    account_id: str,
    body: CommunicationAccountOAuthRefreshRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountOAuthCompleteResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    provider = _oauth_provider_for_account(account)
    settings = _as_dict(account.settings_json)
    oauth_json = _as_dict(settings.get("oauth"))
    refresh_token = _oauth_refresh_token(oauth_json)
    if not refresh_token:
        raise HTTPException(status_code=409, detail="OAuth refresh token is not configured")

    now = _now_utc()
    if body.simulate_refresh:
        oauth_mut = {
            **oauth_json,
            "access_token": f"sim_{provider}_access_{generate_secret(24)}",
            "expires_at": (now + timedelta(seconds=int(body.expires_in or 3600))).isoformat(),
            "oauth_status": "connected",
            "last_error": None,
            "last_refreshed_at": now.isoformat(),
            "provider_payload": {**_as_dict(oauth_json.get("provider_payload")), **_as_dict(body.provider_payload)},
        }
        settings["oauth"] = _normalize_account_settings_for_store({"oauth": oauth_mut}).get("oauth", oauth_mut)
        account.settings_json = settings
        await db.commit()
        await db.refresh(account)
        return CommunicationAccountOAuthCompleteResponse(
            ok=True,
            action="oauth_refresh",
            provider=provider,
            account=_account_out(account),
            detail="OAuth token refreshed (simulated)",
        )

    client_id = str(oauth_json.get("client_id") or "").strip()
    client_secret = _oauth_client_secret(oauth_json)
    if not client_id:
        raise HTTPException(status_code=422, detail="OAuth client_id is required")
    try:
        token_payload = await refresh_oauth_access_token(
            provider=provider,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            scope=str(oauth_json.get("scope") or "").strip() or None,
        )
    except OAuthProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    oauth_mut = {
        **oauth_json,
        "access_token": token_payload.access_token,
        "expires_at": (now + timedelta(seconds=int(token_payload.expires_in or body.expires_in or 3600))).isoformat(),
        "token_type": token_payload.token_type or str(oauth_json.get("token_type") or "Bearer"),
        "scope": token_payload.scope or str(oauth_json.get("scope") or ""),
        "oauth_status": "connected",
        "last_error": None,
        "last_refreshed_at": now.isoformat(),
        "provider_payload": {
            **_as_dict(oauth_json.get("provider_payload")),
            **_as_dict(token_payload.provider_payload),
            **_as_dict(body.provider_payload),
        },
    }
    if token_payload.refresh_token:
        oauth_mut["refresh_token"] = token_payload.refresh_token
    if token_payload.id_token:
        oauth_mut["id_token"] = token_payload.id_token
    settings["oauth"] = _normalize_account_settings_for_store({"oauth": oauth_mut}).get("oauth", oauth_mut)
    account.settings_json = settings
    await db.commit()
    await db.refresh(account)

    return CommunicationAccountOAuthCompleteResponse(
        ok=True,
        action="oauth_refresh",
        provider=provider,
        account=_account_out(account),
        detail="OAuth token refreshed",
    )


@router.get("/accounts/{account_id}/sync-cursor", response_model=CommunicationAccountSyncCursorOut)
async def get_channel_account_sync_cursor(
    account_id: str,
    cursor_key: str = Query(..., min_length=1, max_length=128),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountSyncCursorOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    settings = _as_dict(account.settings_json)
    cursors = _as_dict(settings.get("sync_cursors"))
    row = _as_dict(cursors.get(cursor_key))
    return CommunicationAccountSyncCursorOut(
        account_id=str(account.id),
        cursor_key=cursor_key,
        cursor_value=str(row.get("value")) if row.get("value") is not None else None,
        meta=_as_dict(row.get("meta")),
        updated_at=str(row.get("updated_at")) if row.get("updated_at") is not None else None,
    )


@router.patch("/accounts/{account_id}/sync-cursor", response_model=CommunicationAccountSyncCursorOut)
async def patch_channel_account_sync_cursor(
    account_id: str,
    body: CommunicationAccountSyncCursorPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountSyncCursorOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    settings = _as_dict(account.settings_json)
    cursors = _as_dict(settings.get("sync_cursors"))
    now_iso = _now_utc().isoformat()
    cursors[body.cursor_key] = {
        "value": body.cursor_value,
        "meta": _as_dict(body.meta),
        "updated_at": now_iso,
    }
    settings["sync_cursors"] = cursors
    account.settings_json = settings
    await db.commit()
    await db.refresh(account)
    return CommunicationAccountSyncCursorOut(
        account_id=str(account.id),
        cursor_key=body.cursor_key,
        cursor_value=body.cursor_value,
        meta=_as_dict(body.meta),
        updated_at=now_iso,
    )
