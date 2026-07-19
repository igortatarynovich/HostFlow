"""C5 — Communication Send Pipeline (sole outbound entry).

Chain (fail-closed; never invent Recruitment):
  Thread Result Link → CommunicationContext → Module Policy
  → Template Metadata → transport

Transports must not determine domain or pick templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.context_resolver import (
    CommunicationContext,
    CommunicationContextResolveError,
    resolve_communication_context,
)
from backend.app.communications.policy_contract import CommunicationPolicyDecision
from backend.app.communications.policy_gate import evaluate_policy_for_context
from backend.app.communications.template_enforce import (
    TemplateEnforceDecision,
    enforce_template_metadata,
)
from backend.app.communications.template_metadata import CommunicationTemplateMetadata

PIPELINE_VERSION = "communication.send_pipeline.v1"

REASON_PIPELINE_DENIED = "communication_pipeline_denied"
REASON_TRANSPORT_FAILED = "transport_failed"


@dataclass(frozen=True, slots=True)
class CommunicationSendRequest:
    tenant_id: str
    thread_id: str
    channel: str
    communication_purpose: str
    template: CommunicationTemplateMetadata | None
    locale: str | None = None
    actor_context: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CommunicationSendAuthorization:
    allowed: bool
    reason_code: str | None
    context: CommunicationContext | None
    policy: CommunicationPolicyDecision | None
    template_decision: TemplateEnforceDecision | None
    authorization_id: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "authorization_id": self.authorization_id,
            "context": self.context.to_dict() if self.context else None,
            "policy": self.policy.to_dict() if self.policy else None,
            "template_decision": (
                self.template_decision.to_dict() if self.template_decision else None
            ),
            "details": dict(self.details),
            "pipeline_version": PIPELINE_VERSION,
        }


@dataclass(frozen=True, slots=True)
class CommunicationSendResult:
    status: str  # sent | denied | transport_failed
    authorization: CommunicationSendAuthorization
    provider_ref: str | None = None
    error: str | None = None

    @property
    def allowed(self) -> bool:
        return self.status == "sent"


TransportFn = Callable[[], Awaitable[Any]]


def _denied(
    *,
    reason_code: str,
    context: CommunicationContext | None = None,
    policy: CommunicationPolicyDecision | None = None,
    template_decision: TemplateEnforceDecision | None = None,
    **details: Any,
) -> CommunicationSendAuthorization:
    return CommunicationSendAuthorization(
        allowed=False,
        reason_code=reason_code,
        context=context,
        policy=policy,
        template_decision=template_decision,
        authorization_id=str(uuid4()),
        details=dict(details),
    )


async def authorize_outbound_communication(
    db: AsyncSession,
    request: CommunicationSendRequest,
) -> CommunicationSendAuthorization:
    """Run C1–C4 gates. Does not send."""
    try:
        context = await resolve_communication_context(
            db,
            tenant_id=str(request.tenant_id),
            thread_id=str(request.thread_id),
        )
    except CommunicationContextResolveError as exc:
        return _denied(
            reason_code=str(exc.details.get("reason") or "context_unresolved"),
            details=dict(exc.details),
        )

    policy = evaluate_policy_for_context(
        context,
        communication_purpose=str(request.communication_purpose or ""),
        channel=str(request.channel or ""),
        locale=request.locale,
        actor_context=request.actor_context,
    )
    if not policy.allowed:
        return _denied(
            reason_code=policy.reason_code,
            context=context,
            policy=policy,
            details={"stage": "policy"},
        )

    template_decision = enforce_template_metadata(
        context=context,
        template=request.template,
        channel=str(request.channel or ""),
        communication_purpose=str(request.communication_purpose or ""),
        locale=request.locale,
    )
    if not template_decision.allowed:
        return _denied(
            reason_code=template_decision.reason_code,
            context=context,
            policy=policy,
            template_decision=template_decision,
            details={"stage": "template_metadata", "fallback": None},
        )

    return CommunicationSendAuthorization(
        allowed=True,
        reason_code="authorized",
        context=context,
        policy=policy,
        template_decision=template_decision,
        authorization_id=str(uuid4()),
        details={"pipeline_version": PIPELINE_VERSION},
    )


async def send_via_communication_pipeline(
    db: AsyncSession,
    request: CommunicationSendRequest,
    *,
    transport: TransportFn,
) -> CommunicationSendResult:
    """Authorize via C1–C4 then invoke transport. Retries must call this again."""
    auth = await authorize_outbound_communication(db, request)
    if not auth.allowed:
        return CommunicationSendResult(
            status="denied",
            authorization=auth,
            error=auth.reason_code,
        )
    try:
        provider_ref = await transport()
    except Exception as exc:  # noqa: BLE001 — surface as transport failure
        return CommunicationSendResult(
            status="transport_failed",
            authorization=auth,
            error=str(exc)[:500],
        )
    return CommunicationSendResult(
        status="sent",
        authorization=auth,
        provider_ref=str(provider_ref) if provider_ref is not None else None,
    )


def template_metadata_from_mapping(
    raw: dict[str, Any] | None,
) -> CommunicationTemplateMetadata | None:
    """Parse template_metadata_v1 from message/dispatch payload."""
    if not isinstance(raw, dict):
        return None
    from backend.app.communications.template_metadata import build_template_metadata

    try:
        channels = raw.get("supported_channels") or []
        locales = raw.get("supported_locales") or []
        return build_template_metadata(
            template_id=str(raw.get("template_id") or ""),
            template_version=str(raw.get("template_version") or ""),
            module_owner=str(raw.get("module_owner") or ""),
            communication_domain=str(raw.get("communication_domain") or ""),
            communication_purpose=str(raw.get("communication_purpose") or ""),
            supported_channels=list(channels) if isinstance(channels, (list, set, frozenset)) else [],
            supported_locales=list(locales) if isinstance(locales, (list, set, frozenset)) else [],
            lifecycle_status=str(raw.get("lifecycle_status") or "active"),
            policy_version=str(raw.get("policy_version") or ""),
        )
    except Exception:  # noqa: BLE001
        return None
