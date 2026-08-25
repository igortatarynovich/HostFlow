"""C2.2 PR-3 — Intent Emitter.

Only path from Automation → platform:

    EvaluationResult(fire) → IntentExecutionRequest → execute_communication_intent

No Thread mutation, no provider/sender shortcut, no Campaign.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.automation.errors import AutomationDomainError
from backend.app.communications.automation.evaluator.types import (
    OUTCOME_FIRE,
    OUTCOME_SKIP,
    EvaluationResult,
)
from backend.app.communications.automation.lifecycle import record_decision
from backend.app.communications.command import CommunicationOrigin, CommunicationRecipient
from backend.app.communications.execute_intent import (
    IntentExecutionRequest,
    IntentRenderResult,
    execute_communication_intent,
    render_communication_intent,
)
from backend.app.communications.link_resolver import LinkResolveRequest, LinkResolver
from backend.app.communications.send_communication import (
    SendCommunicationResult,
    TransportFn,
)
from backend.app.communications.template_resolver import TemplateResolver
from backend.app.models.communication_automation import CommunicationAutomationDecision


@dataclass(frozen=True, slots=True)
class EmitContext:
    """Caller-supplied origin/recipients for Intent emission.

    Recipient strategy from the rule is recorded in meta; concrete addresses
    are supplied here (resolver expansion lands with event wiring later).
    """

    tenant_id: str
    origin: CommunicationOrigin
    recipients: Sequence[CommunicationRecipient]
    locale: str | None = None
    actor_id: str | None = None
    own_company_id: str | None = None
    related_entities: Sequence[CommunicationOrigin] = ()
    thread_id: str | None = None
    idempotency_key: str | None = None
    purpose: str | None = None
    delivery_purpose: str | None = None
    thread_subject: str | None = None
    link_requests: Sequence[LinkResolveRequest] = ()
    channel_override: str | None = None
    extra_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EmitResult:
    evaluation: EvaluationResult
    emitted: bool
    intent_request: IntentExecutionRequest | None
    decision: CommunicationAutomationDecision | None
    render_result: IntentRenderResult | None = None
    execute_result: SendCommunicationResult | None = None
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "emitted": self.emitted,
            "skip_reason": self.skip_reason,
            "outcome": self.evaluation.outcome,
            "rule_id": self.evaluation.rule_id,
            "rule_version_id": self.evaluation.rule_version_id,
            "source_event_id": self.evaluation.source_event_id,
            "intent_key": (
                self.intent_request.intent
                if self.intent_request is not None
                else self.evaluation.intent_key
            ),
            "decision_id": str(self.decision.id) if self.decision is not None else None,
            "message_id": (
                getattr(self.execute_result, "message_id", None)
                if self.execute_result is not None
                else None
            ),
        }


def automation_identity_for(evaluation: EvaluationResult) -> str:
    return f"comm_automation:{evaluation.rule_id}:{evaluation.rule_version_id}"


def build_intent_request(
    evaluation: EvaluationResult,
    context: EmitContext,
) -> IntentExecutionRequest:
    """Build IntentExecutionRequest from a fire evaluation. No I/O."""
    if evaluation.outcome != OUTCOME_FIRE:
        raise AutomationDomainError(
            "emit_requires_fire",
            "Only fire evaluations may build an IntentExecutionRequest",
            details={
                "outcome": evaluation.outcome,
                "reason_codes": list(evaluation.reason_codes),
            },
        )
    intent_key = str(evaluation.intent_key or "").strip()
    if not intent_key:
        raise AutomationDomainError(
            "emit_intent_key_missing",
            "Fire evaluation missing intent_key",
            details={"rule_version_id": evaluation.rule_version_id},
        )
    if not context.recipients:
        raise AutomationDomainError(
            "emit_recipients_required",
            "EmitContext.recipients is required",
            details={"rule_id": evaluation.rule_id},
        )

    channel = (
        str(context.channel_override or evaluation.channel or "email").strip().lower()
        or "email"
    )
    identity = automation_identity_for(evaluation)
    meta: dict[str, Any] = {
        "automation_rule_id": evaluation.rule_id,
        "automation_rule_version_id": evaluation.rule_version_id,
        "automation_reason_codes": list(evaluation.reason_codes),
        "automation_recipient_strategy": evaluation.recipient_strategy,
        "automation_matched_trigger": evaluation.matched_trigger_event_type,
        "automation_recipient_config": dict(evaluation.recipient_config or {}),
        **dict(context.extra_meta or {}),
    }

    return IntentExecutionRequest(
        tenant_id=str(context.tenant_id),
        intent=intent_key,
        origin=context.origin,
        recipients=tuple(context.recipients),
        channel=channel,
        locale=context.locale,
        template_variables=dict(evaluation.template_variables or {}),
        link_requests=tuple(context.link_requests or ()),
        actor_id=context.actor_id,
        automation_identity=identity,
        own_company_id=context.own_company_id,
        related_entities=tuple(context.related_entities or ()),
        thread_id=context.thread_id,
        idempotency_key=context.idempotency_key
        or f"auto:{evaluation.rule_version_id}:{evaluation.source_event_id}",
        purpose=context.purpose,
        delivery_purpose=context.delivery_purpose,
        thread_subject=context.thread_subject,
        correlation_id=evaluation.correlation_id,
        source_event_id=evaluation.source_event_id,
        preferred_template_key=evaluation.preferred_template_key,
        meta=meta,
    )


async def emit_from_evaluation(
    db: AsyncSession,
    evaluation: EvaluationResult,
    context: EmitContext,
    *,
    persist_decision: bool = True,
    mode: str = "execute",
    skip_transport: bool = True,
    transport: TransportFn | None = None,
    template_resolver: TemplateResolver | None = None,
    link_resolver: LinkResolver | None = None,
) -> EmitResult:
    """Emit Intent into the platform pipeline for a fire evaluation.

    ``mode``:
      - ``request_only`` — build request + record decision (no render/execute)
      - ``render`` — render Command via platform (no persist send)
      - ``execute`` — full ``execute_communication_intent`` (default ``skip_transport=True``)

    Skip evaluations never create Intent; they may still record a skip decision.
    """
    mode_norm = str(mode or "execute").strip().lower()
    if mode_norm not in {"request_only", "render", "execute"}:
        raise AutomationDomainError(
            "invalid_emit_mode",
            f"mode must be request_only|render|execute, got {mode!r}",
        )

    if evaluation.outcome != OUTCOME_FIRE:
        decision = None
        if persist_decision:
            decision = await record_decision(
                db,
                tenant_id=context.tenant_id,
                rule_id=evaluation.rule_id,
                rule_version_id=evaluation.rule_version_id,
                source_event_id=evaluation.source_event_id,
                event_type=evaluation.event_type,
                outcome=OUTCOME_SKIP,
                reason_codes=list(evaluation.reason_codes),
                intent_key=evaluation.intent_key,
                correlation_id=evaluation.correlation_id,
                meta={"emit": "skipped"},
            )
        return EmitResult(
            evaluation=evaluation,
            emitted=False,
            intent_request=None,
            decision=decision,
            skip_reason=(
                evaluation.reason_codes[0]
                if evaluation.reason_codes
                else evaluation.outcome
            ),
        )

    request = build_intent_request(evaluation, context)
    snapshot = {
        "intent": str(request.intent),
        "channel": request.channel,
        "automation_identity": request.automation_identity,
        "source_event_id": request.source_event_id,
        "preferred_template_key": request.preferred_template_key,
        "template_variables": dict(request.template_variables or {}),
        "recipient_count": len(request.recipients),
        "origin": {
            "entity_type": request.origin.entity_type,
            "entity_id": request.origin.entity_id,
        },
    }

    render_result: IntentRenderResult | None = None
    execute_result: SendCommunicationResult | None = None

    if mode_norm == "render":
        render_result = await render_communication_intent(
            request,
            template_resolver=template_resolver,
            link_resolver=link_resolver,
        )
    elif mode_norm == "execute":
        execute_result = await execute_communication_intent(
            db,
            request,
            transport=transport,
            skip_transport=skip_transport,
            template_resolver=template_resolver,
            link_resolver=link_resolver,
        )

    decision = None
    if persist_decision:
        decision = await record_decision(
            db,
            tenant_id=context.tenant_id,
            rule_id=evaluation.rule_id,
            rule_version_id=evaluation.rule_version_id,
            source_event_id=evaluation.source_event_id,
            event_type=evaluation.event_type,
            outcome=OUTCOME_FIRE,
            reason_codes=list(evaluation.reason_codes),
            intent_key=str(request.intent),
            intent_request_snapshot=snapshot,
            correlation_id=evaluation.correlation_id,
            meta={
                "emit_mode": mode_norm,
                "skip_transport": skip_transport if mode_norm == "execute" else None,
            },
        )

    return EmitResult(
        evaluation=evaluation,
        emitted=True,
        intent_request=request,
        decision=decision,
        render_result=render_result,
        execute_result=execute_result,
    )


__all__ = [
    "EmitContext",
    "EmitResult",
    "automation_identity_for",
    "build_intent_request",
    "emit_from_evaluation",
]
