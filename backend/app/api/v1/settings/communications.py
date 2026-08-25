from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.api.v1.tenants import service as tenant_service
from backend.app.constants.hostflow_canonical_tenants import is_focus_personnel_tenant
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.plan_feature_gates import plan_allows_smart_operations_bundle, resolve_tenant_plan_code


router = APIRouter(prefix="/communications", tags=["settings-communications"], redirect_slashes=False)

_ESCALATION_TARGET_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
_RESERVED_ESCALATION_TARGETS = {"all", "none", "default", "system", "auto", "role", "queue", "user"}


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    if (ctx.role or "").strip().lower() == Role.superadmin.value:
        return
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for tenant")


ChannelKey = Literal["whatsapp", "telegram", "viber", "messenger", "instagram", "sms", "email"]
RoutingMode = Literal["manual", "round_robin", "candidate_manager"]
PlannerView = Literal["agenda", "week"]
QueueStrategy = Literal["manual", "round_robin", "weighted_round_robin", "least_busy"]
AvailabilityState = Literal["available", "busy", "offline", "break", "meeting"]
SlaRecipientMode = Literal["assignee_or_owner", "assignee_only", "owner_only"]
CommModuleKey = Literal["messages", "email", "calendar", "planner", "availability", "timeOff", "communicationsAdmin"]
CommandActionType = Literal[
    "mark_read",
    "archive",
    "unarchive",
    "delete",
    "restore",
    "priority_high",
    "priority_normal",
    "tag_add",
    "tag_remove",
    "move_folder",
]
MessageTemplateVisibility = Literal["private", "company"]
MessageTemplateTarget = Literal["messages", "email", "both"]


class CommunicationChannelConfig(BaseModel):
    key: ChannelKey
    enabled: bool = False
    inboundEnabled: bool = True
    outboundEnabled: bool = True
    routingMode: RoutingMode = "manual"
    responseSlaMinutes: int = Field(default=30, ge=5, le=1440)


class CommunicationsChannelsSettings(BaseModel):
    businessHoursStart: str = "08:00"
    businessHoursEnd: str = "18:00"
    timezone: str = "Europe/Warsaw"
    channels: List[CommunicationChannelConfig] = Field(default_factory=list)
    candidateReplyTemplate: str = ""
    clientReplyTemplate: str = ""
    consentRequired: bool = True


class CommunicationsEmailWorkflowSettings(BaseModel):
    incomingEnabled: bool = False
    incomingAlias: str = ""
    autoThreading: bool = True
    syncIntervalMinutes: int = Field(default=5, ge=1, le=1440)
    defaultMailbox: Literal["candidates", "clients", "operations"] = "candidates"
    signatureCandidates: str = ""
    signatureClients: str = ""


class PlannerSettings(BaseModel):
    view: PlannerView = "agenda"
    workStart: str = "08:00"
    workEnd: str = "18:00"
    showWeekends: bool = False
    slotMinutes: Literal[15, 30, 60] = 30


class ManagerScheduleSlot(BaseModel):
    day: Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    start: str = "09:00"
    end: str = "17:00"
    enabled: bool = True


class ManagerAvailability(BaseModel):
    state: AvailabilityState = "available"
    note: str = ""
    busyUntil: str | None = None
    currentLoad: int = Field(default=0, ge=0)
    maxConcurrentChats: int = Field(default=10, ge=1, le=500)
    maxConcurrentCalls: int = Field(default=3, ge=1, le=100)


class ManagerQueueItem(BaseModel):
    managerId: str
    enabled: bool = True
    priorityWeight: int = Field(default=100, ge=1, le=1000)
    queueOrder: int = Field(default=0, ge=0, le=10000)
    skills: List[str] = Field(default_factory=list)
    channels: List[ChannelKey] = Field(default_factory=list)
    languageCodes: List[str] = Field(default_factory=list)
    candidateTypes: List[str] = Field(default_factory=list)
    schedule: List[ManagerScheduleSlot] = Field(default_factory=list)
    availability: ManagerAvailability = Field(default_factory=ManagerAvailability)


class ManagerQueueSettings(BaseModel):
    enabled: bool = True
    strategy: QueueStrategy = "round_robin"
    fallbackToManual: bool = True
    rebalanceOnStatusChange: bool = True
    respectSchedules: bool = True
    respectAvailability: bool = True
    items: List[ManagerQueueItem] = Field(default_factory=list)


class CommunicationsComplianceSettings(BaseModel):
    requireConsentForOutboundCandidateMessaging: bool = True
    allowClientMessagingWithoutConsent: bool = True
    auditRetentionDays: int = Field(default=365, ge=30, le=3650)
    maskCandidateDataInClientThreads: bool = True


class CommunicationsSlaSettings(BaseModel):
    enabled: bool = True
    createNotifications: bool = True
    createReminders: bool = True
    recipientMode: SlaRecipientMode = "assignee_or_owner"
    mutedChannels: List[ChannelKey] = Field(default_factory=list)
    escalationTargets: List[str] = Field(default_factory=list)


class CommunicationsModuleEntitlement(BaseModel):
    enabled: bool = True
    planRequired: Literal["starter", "pro", "enterprise"] | None = None
    seatScoped: bool = False


class CommunicationsEntitlementsSettings(BaseModel):
    modules: Dict[CommModuleKey, CommunicationsModuleEntitlement] = Field(default_factory=dict)


class CommunicationsPlanSnapshotOut(BaseModel):
    """Server-computed subscription signals (not persisted in ``tenant.settings``)."""

    smartOperations: bool = False


class CommunicationsRoleAccessSettings(BaseModel):
    messages: List[str] = Field(default_factory=lambda: ["administrator", "supervisor", "recruiter", "client_manager", "client_processor"])
    email: List[str] = Field(default_factory=lambda: ["administrator", "supervisor", "recruiter", "client_manager"])
    calendar: List[str] = Field(default_factory=lambda: ["administrator", "supervisor", "recruiter", "client_manager"])
    planner: List[str] = Field(default_factory=lambda: ["administrator", "supervisor", "recruiter", "client_manager"])
    teamAvailability: List[str] = Field(default_factory=lambda: ["administrator", "supervisor"])
    myAvailability: List[str] = Field(default_factory=lambda: ["administrator", "supervisor", "recruiter", "client_manager", "client_processor"])
    timeOffRequests: List[str] = Field(default_factory=lambda: ["administrator", "supervisor", "recruiter", "client_manager", "client_processor"])
    communicationsAdmin: List[str] = Field(default_factory=lambda: ["administrator", "supervisor"])


class CommunicationsAccessSettings(BaseModel):
    roles: CommunicationsRoleAccessSettings = Field(default_factory=CommunicationsRoleAccessSettings)
    usersOverrides: Dict[str, Dict[str, bool]] = Field(default_factory=dict)


class CommunicationCommandAction(BaseModel):
    type: CommandActionType
    value: str | None = None


class CommunicationCommandTemplate(BaseModel):
    id: str
    label: str
    target: Literal["email", "messages", "both"] = "both"
    enabled: bool = True
    actions: List[CommunicationCommandAction] = Field(default_factory=list)


class CommunicationsCommandsSettings(BaseModel):
    items: List[CommunicationCommandTemplate] = Field(default_factory=list)


class CommunicationMessageTemplate(BaseModel):
    id: str
    label: str
    body: str = ""
    visibility: MessageTemplateVisibility = "private"
    target: MessageTemplateTarget = "messages"
    ownerUserId: str | None = None
    enabled: bool = True


class CommunicationsMessageTemplatesSettings(BaseModel):
    items: List[CommunicationMessageTemplate] = Field(default_factory=list)


class CommunicationsSettingsOut(BaseModel):
    channels: CommunicationsChannelsSettings
    email: CommunicationsEmailWorkflowSettings
    planner: PlannerSettings
    managerQueue: ManagerQueueSettings
    sla: CommunicationsSlaSettings
    compliance: CommunicationsComplianceSettings
    entitlements: CommunicationsEntitlementsSettings
    access: CommunicationsAccessSettings
    commands: CommunicationsCommandsSettings
    messageTemplates: CommunicationsMessageTemplatesSettings
    plan: CommunicationsPlanSnapshotOut = Field(default_factory=CommunicationsPlanSnapshotOut)


class CommunicationsSettingsPatch(BaseModel):
    channels: CommunicationsChannelsSettings | None = None
    email: CommunicationsEmailWorkflowSettings | None = None
    planner: PlannerSettings | None = None
    managerQueue: ManagerQueueSettings | None = None
    sla: CommunicationsSlaSettings | None = None
    compliance: CommunicationsComplianceSettings | None = None
    entitlements: CommunicationsEntitlementsSettings | None = None
    access: CommunicationsAccessSettings | None = None
    commands: CommunicationsCommandsSettings | None = None
    messageTemplates: CommunicationsMessageTemplatesSettings | None = None


DEFAULT_CHANNELS: List[Dict[str, Any]] = [
    {"key": "whatsapp", "enabled": False, "inboundEnabled": True, "outboundEnabled": True, "routingMode": "candidate_manager", "responseSlaMinutes": 30},
    {"key": "telegram", "enabled": False, "inboundEnabled": True, "outboundEnabled": True, "routingMode": "manual", "responseSlaMinutes": 30},
    {"key": "viber", "enabled": False, "inboundEnabled": True, "outboundEnabled": True, "routingMode": "manual", "responseSlaMinutes": 60},
    {"key": "messenger", "enabled": False, "inboundEnabled": True, "outboundEnabled": False, "routingMode": "round_robin", "responseSlaMinutes": 30},
    {"key": "instagram", "enabled": False, "inboundEnabled": True, "outboundEnabled": False, "routingMode": "round_robin", "responseSlaMinutes": 30},
    {"key": "sms", "enabled": True, "inboundEnabled": False, "outboundEnabled": True, "routingMode": "manual", "responseSlaMinutes": 15},
    {"key": "email", "enabled": True, "inboundEnabled": True, "outboundEnabled": True, "routingMode": "candidate_manager", "responseSlaMinutes": 120},
]


def _default_settings() -> Dict[str, Any]:
    return {
        "channels": {
            "businessHoursStart": "08:00",
            "businessHoursEnd": "18:00",
            "timezone": "Europe/Warsaw",
            "channels": list(DEFAULT_CHANNELS),
            "candidateReplyTemplate": "Здравствуйте! Получили ваше сообщение. Ответим в ближайшее время.",
            "clientReplyTemplate": "Dzień dobry, wiadomość została przyjęta do obsługi. Wrócimy z odpowiedzią możliwie szybko.",
            "consentRequired": True,
        },
        "email": {
            "incomingEnabled": False,
            "incomingAlias": "",
            "autoThreading": True,
            "syncIntervalMinutes": 5,
            "defaultMailbox": "candidates",
            "signatureCandidates": "",
            "signatureClients": "",
        },
        "planner": {
            "view": "agenda",
            "workStart": "08:00",
            "workEnd": "18:00",
            "showWeekends": False,
            "slotMinutes": 30,
        },
        "managerQueue": {
            "enabled": True,
            "strategy": "round_robin",
            "fallbackToManual": True,
            "rebalanceOnStatusChange": True,
            "respectSchedules": True,
            "respectAvailability": True,
            "items": [],
        },
        "sla": {
            "enabled": True,
            "createNotifications": True,
            "createReminders": True,
            "recipientMode": "assignee_or_owner",
            "mutedChannels": [],
            "escalationTargets": ["priority", "manual_review", "supervisor_desk"],
        },
        "compliance": {
            "requireConsentForOutboundCandidateMessaging": True,
            "allowClientMessagingWithoutConsent": True,
            "auditRetentionDays": 365,
            "maskCandidateDataInClientThreads": True,
        },
        "entitlements": {
            "modules": {
                "messages": {"enabled": True, "planRequired": None, "seatScoped": False},
                "email": {"enabled": True, "planRequired": "pro", "seatScoped": False},
                "calendar": {"enabled": True, "planRequired": None, "seatScoped": False},
                "planner": {"enabled": True, "planRequired": None, "seatScoped": False},
                "availability": {"enabled": True, "planRequired": None, "seatScoped": True},
                "timeOff": {"enabled": True, "planRequired": "pro", "seatScoped": True},
                "communicationsAdmin": {"enabled": True, "planRequired": None, "seatScoped": False},
            }
        },
        "access": {
            "roles": CommunicationsRoleAccessSettings().model_dump(mode="json"),
            "usersOverrides": {},
        },
        "commands": {
            "items": [
                {
                    "id": "cmd_archive_done",
                    "label": "Archive completed",
                    "target": "both",
                    "enabled": True,
                    "actions": [{"type": "mark_read"}, {"type": "archive"}],
                },
                {
                    "id": "cmd_escalate_high",
                    "label": "Escalate priority",
                    "target": "both",
                    "enabled": True,
                    "actions": [{"type": "priority_high"}, {"type": "tag_add", "value": "escalation"}],
                },
                {
                    "id": "cmd_handoff_ready",
                    "label": "Ready for handoff",
                    "target": "both",
                    "enabled": True,
                    "actions": [{"type": "tag_add", "value": "handoff_ready"}, {"type": "mark_read"}],
                },
                {
                    "id": "cmd_no_response_followup",
                    "label": "No response follow-up",
                    "target": "both",
                    "enabled": True,
                    "actions": [{"type": "tag_add", "value": "followup_needed"}, {"type": "priority_high"}],
                },
                {
                    "id": "cmd_move_to_hr",
                    "label": "Move to HR folder",
                    "target": "email",
                    "enabled": True,
                    "actions": [{"type": "move_folder", "value": "HR"}],
                },
            ]
        },
        "messageTemplates": {
            "items": [
                {
                    "id": "msg_tpl_acknowledge",
                    "label": "Acknowledge received",
                    "body": "Thank you, we received your message and will reply shortly.",
                    "visibility": "company",
                    "target": "messages",
                    "ownerUserId": None,
                    "enabled": True,
                    # C5/INV-17: UI copy only. Outbound dispatch requires
                    # Communication Pipeline purpose + template_metadata_v1.
                },
                {
                    "id": "msg_tpl_docs_request",
                    "label": "Request documents",
                    "body": "Please send the requested documents at your earliest convenience.",
                    "visibility": "company",
                    "target": "both",
                    "ownerUserId": None,
                    "enabled": True,
                },
            ]
        },
    }


def _normalize_escalation_targets(raw: Any, *, strict: bool) -> List[str]:
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    seen: set[str] = set()
    for value in raw:
        target = str(value or "").strip().lower()
        if not target:
            continue
        if not _ESCALATION_TARGET_RE.match(target):
            if strict:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": "sla_escalation_target_invalid",
                        "message": "Escalation target must match ^[a-z][a-z0-9_-]{1,63}$",
                        "target": target,
                    },
                )
            continue
        if target in _RESERVED_ESCALATION_TARGETS:
            if strict:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": "sla_escalation_target_reserved",
                        "message": "Escalation target uses reserved identifier",
                        "target": target,
                    },
                )
            continue
        if target in seen:
            continue
        seen.add(target)
        out.append(target)
    return out


def _apply_focus_personnel_default_features(merged: Dict[str, Any], tenant_id: str) -> None:
    """
    Focus Personnel (in-house agency): all communication toggles and module
    entitlements on by default (merged over stored settings for API responses).
    """
    if not is_focus_personnel_tenant(tenant_id):
        return
    ch = merged.get("channels")
    if isinstance(ch, dict) and isinstance(ch.get("channels"), list):
        for row in ch["channels"]:
            if isinstance(row, dict):
                row["enabled"] = True
                row["inboundEnabled"] = True
                row["outboundEnabled"] = True
    em = merged.get("email")
    if isinstance(em, dict):
        em["incomingEnabled"] = True
    ent = merged.get("entitlements")
    if isinstance(ent, dict) and isinstance(ent.get("modules"), dict):
        for m in ent["modules"].values():
            if isinstance(m, dict):
                m["enabled"] = True
                m["planRequired"] = None


def _extract_settings(tenant_obj: Any) -> Dict[str, Any]:
    tenant_settings = tenant_obj.settings if isinstance(getattr(tenant_obj, "settings", None), dict) else {}
    raw = tenant_settings.get("communications")
    if not isinstance(raw, dict):
        return _default_settings()
    merged = _default_settings()
    for key in ["channels", "email", "planner", "managerQueue", "sla", "compliance", "entitlements", "access", "commands", "messageTemplates"]:
        if isinstance(raw.get(key), dict):
            merged[key] = {**merged[key], **raw[key]}
    # channels list and queue items are list types (replace entirely if valid list)
    if isinstance(raw.get("channels"), dict) and isinstance(raw["channels"].get("channels"), list):
        merged["channels"]["channels"] = raw["channels"]["channels"]
    if isinstance(raw.get("managerQueue"), dict) and isinstance(raw["managerQueue"].get("items"), list):
        merged["managerQueue"]["items"] = raw["managerQueue"]["items"]
    if isinstance(raw.get("commands"), dict) and isinstance(raw["commands"].get("items"), list):
        merged["commands"]["items"] = raw["commands"]["items"]
    if isinstance(raw.get("messageTemplates"), dict) and isinstance(raw["messageTemplates"].get("items"), list):
        merged["messageTemplates"]["items"] = raw["messageTemplates"]["items"]
    if isinstance(merged.get("sla"), dict):
        merged["sla"]["escalationTargets"] = _normalize_escalation_targets(
            merged["sla"].get("escalationTargets"),
            strict=False,
        )
    tid = str(getattr(tenant_obj, "id", "") or "").strip()
    if tid:
        _apply_focus_personnel_default_features(merged, tid)
    return merged


def _apply_patch(current: Dict[str, Any], patch: CommunicationsSettingsPatch) -> Dict[str, Any]:
    next_payload = dict(current)
    if patch.channels is not None:
        next_payload["channels"] = patch.channels.model_dump(mode="json")
    if patch.email is not None:
        next_payload["email"] = patch.email.model_dump(mode="json")
    if patch.planner is not None:
        next_payload["planner"] = patch.planner.model_dump(mode="json")
    if patch.managerQueue is not None:
        next_payload["managerQueue"] = patch.managerQueue.model_dump(mode="json")
    if patch.sla is not None:
        sla_payload = patch.sla.model_dump(mode="json")
        sla_payload["escalationTargets"] = _normalize_escalation_targets(
            sla_payload.get("escalationTargets"),
            strict=True,
        )
        next_payload["sla"] = sla_payload
    if patch.compliance is not None:
        next_payload["compliance"] = patch.compliance.model_dump(mode="json")
    if patch.entitlements is not None:
        next_payload["entitlements"] = patch.entitlements.model_dump(mode="json")
    if patch.access is not None:
        next_payload["access"] = patch.access.model_dump(mode="json")
    if patch.commands is not None:
        next_payload["commands"] = patch.commands.model_dump(mode="json")
    if patch.messageTemplates is not None:
        next_payload["messageTemplates"] = patch.messageTemplates.model_dump(mode="json")
    return next_payload


async def _communications_settings_out(db: AsyncSession, tenant_id: str, tenant: Any) -> CommunicationsSettingsOut:
    """Merge stored settings with **server-computed** ``plan`` (subscription signals)."""
    raw = _extract_settings(tenant)
    plan_code = await resolve_tenant_plan_code(db, tenant_id)
    base = CommunicationsSettingsOut.model_validate(raw)
    return base.model_copy(
        update={
            "plan": CommunicationsPlanSnapshotOut(
                smartOperations=plan_allows_smart_operations_bundle(plan_code, tenant_id=tenant_id)
            )
        }
    )


@router.get(
    "",
    response_model=CommunicationsSettingsOut,
    dependencies=[
        Depends(
            require_trust_read()
        )
    ],
)
async def get_communications_settings(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> CommunicationsSettingsOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    assert_comm_feature_access(tenant=tenant, current_user=ctx, tenant_id=tenant_id, feature="communicationsAdmin")
    return await _communications_settings_out(db, tenant_id, tenant)


@router.patch(
    "",
    response_model=CommunicationsSettingsOut,
    dependencies=[Depends(require_trust_write())],
)
async def patch_communications_settings(
    patch: CommunicationsSettingsPatch,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> CommunicationsSettingsOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    assert_comm_feature_access(tenant=tenant, current_user=ctx, tenant_id=tenant_id, feature="communicationsAdmin")
    current = _extract_settings(tenant)
    next_settings = _apply_patch(current, patch)
    tenant_settings = tenant.settings if isinstance(tenant.settings, dict) else {}
    updated_root = {**tenant_settings, "communications": next_settings}
    tenant = await tenant_service.update_tenant(db, tenant, {"settings": updated_root})
    return await _communications_settings_out(db, tenant_id, tenant)
