"""C2.3 PR-3 — Campaign Intent Emitter.

Only path from Campaign → platform:

    allowed RunItem → IntentExecutionRequest → execute_communication_intent

No Thread mutation shortcut, no provider/sender, no Workspace Commands.
One failed item does not stop the rest of the run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.communications.campaign.errors import CampaignDomainError
from backend.app.communications.campaign.lifecycle import get_run, mark_run_item_outcome
from backend.app.communications.command import CommunicationOrigin, CommunicationRecipient
from backend.app.communications.execute_intent import (
    IntentExecutionRequest,
    IntentRenderResult,
    execute_communication_intent,
    render_communication_intent,
)
from backend.app.communications.link_resolver import LinkResolveRequest, LinkResolver
from backend.app.communications.send_communication import (
    SendCommunicationError,
    SendCommunicationResult,
    TransportFn,
)
from backend.app.communications.template_resolver import TemplateResolver
from backend.app.models.communication_campaign import (
    RUN_ITEM_STATUS_EMITTED,
    RUN_ITEM_STATUS_FAILED,
    RUN_ITEM_STATUS_PENDING,
    RUN_ITEM_STATUS_READY,
    RUN_ITEM_STATUS_SKIPPED,
    CommunicationCampaignRecipient,
    CommunicationCampaignRun,
    CommunicationCampaignRunItem,
    CommunicationCampaignVersion,
)

_EMITTABLE = frozenset({RUN_ITEM_STATUS_PENDING, RUN_ITEM_STATUS_READY})


@dataclass(frozen=True, slots=True)
class CampaignItemEmitInput:
    """Pure snapshot of one RunItem + pinned version plan (no ORM)."""

    tenant_id: str
    campaign_id: str
    campaign_version_id: str
    run_id: str
    run_item_id: str
    recipient_id: str
    intent_key: str
    preferred_template_key: str | None
    channel: str | None
    entity_type: str
    entity_id: str
    address: str
    label: str | None = None
    template_variables: Mapping[str, Any] = field(default_factory=dict)
    source_event_id: str | None = None


@dataclass(frozen=True, slots=True)
class CampaignEmitContext:
    """Caller-supplied extras for Intent emission (locale, actor, overrides)."""

    locale: str | None = None
    actor_id: str | None = None
    own_company_id: str | None = None
    related_entities: Sequence[CommunicationOrigin] = ()
    thread_id: str | None = None
    purpose: str | None = None
    delivery_purpose: str | None = None
    thread_subject: str | None = None
    link_requests: Sequence[LinkResolveRequest] = ()
    channel_override: str | None = None
    correlation_id: str | None = None
    extra_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ItemEmitResult:
    run_item_id: str
    emitted: bool
    intent_request: IntentExecutionRequest | None
    render_result: IntentRenderResult | None = None
    execute_result: SendCommunicationResult | None = None
    skip_reason: str | None = None
    error_code: str | None = None
    item_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_item_id": self.run_item_id,
            "emitted": self.emitted,
            "skip_reason": self.skip_reason,
            "error_code": self.error_code,
            "item_status": self.item_status,
            "intent_key": (
                self.intent_request.intent if self.intent_request is not None else None
            ),
            "message_id": (
                getattr(self.execute_result, "message_id", None)
                if self.execute_result is not None
                else None
            ),
        }


def campaign_identity_for(*, campaign_id: str, campaign_version_id: str) -> str:
    return f"comm_campaign:{campaign_id}:{campaign_version_id}"


def build_intent_request(
    item: CampaignItemEmitInput,
    context: CampaignEmitContext | None = None,
) -> IntentExecutionRequest:
    """Build IntentExecutionRequest for one allowed RunItem. No I/O."""
    ctx = context or CampaignEmitContext()
    intent_key = str(item.intent_key or "").strip()
    if not intent_key:
        raise CampaignDomainError(
            "emit_intent_key_missing",
            "CampaignVersion missing intent_key",
            details={"campaign_version_id": item.campaign_version_id},
        )
    address = str(item.address or "").strip()
    if not address:
        raise CampaignDomainError(
            "emit_address_required",
            "RunItem recipient missing address",
            details={"run_item_id": item.run_item_id},
        )
    entity_type = str(item.entity_type or "").strip()
    entity_id = str(item.entity_id or "").strip()
    if not entity_type or not entity_id:
        raise CampaignDomainError(
            "emit_origin_required",
            "Recipient entity_type and entity_id are required for Intent origin",
            details={"run_item_id": item.run_item_id},
        )

    channel = (
        str(ctx.channel_override or item.channel or "email").strip().lower() or "email"
    )
    source_event_id = (
        str(item.source_event_id or "").strip()
        or f"campaign:{item.run_id}:{item.run_item_id}"
    )
    identity = campaign_identity_for(
        campaign_id=item.campaign_id,
        campaign_version_id=item.campaign_version_id,
    )
    meta: dict[str, Any] = {
        "campaign_id": item.campaign_id,
        "campaign_version_id": item.campaign_version_id,
        "campaign_run_id": item.run_id,
        "campaign_run_item_id": item.run_item_id,
        "campaign_recipient_id": item.recipient_id,
        **dict(ctx.extra_meta or {}),
    }

    return IntentExecutionRequest(
        tenant_id=str(item.tenant_id),
        intent=intent_key,
        origin=CommunicationOrigin(entity_type=entity_type, entity_id=entity_id),
        recipients=(
            CommunicationRecipient(
                address=address,
                label=(str(item.label).strip() if item.label else None),
                recipient_type=entity_type,
                recipient_id=entity_id,
            ),
        ),
        channel=channel,
        locale=ctx.locale,
        template_variables=dict(item.template_variables or {}),
        link_requests=tuple(ctx.link_requests or ()),
        actor_id=ctx.actor_id,
        automation_identity=identity,
        own_company_id=ctx.own_company_id,
        related_entities=tuple(ctx.related_entities or ()),
        thread_id=ctx.thread_id,
        idempotency_key=f"campaign:{item.run_id}:{item.run_item_id}",
        purpose=ctx.purpose,
        delivery_purpose=ctx.delivery_purpose,
        thread_subject=ctx.thread_subject,
        correlation_id=ctx.correlation_id,
        source_event_id=source_event_id,
        preferred_template_key=item.preferred_template_key,
        meta=meta,
    )


def _item_to_input(
    *,
    tenant_id: str,
    run: CommunicationCampaignRun,
    version: CommunicationCampaignVersion,
    item: CommunicationCampaignRunItem,
    recipient: CommunicationCampaignRecipient,
) -> CampaignItemEmitInput:
    snap = dict(recipient.snapshot or {})
    # Prefer explicit template vars bag if present; else use frozen snapshot.
    variables = snap.get("template_variables")
    if isinstance(variables, Mapping):
        template_variables = dict(variables)
    else:
        template_variables = {k: v for k, v in snap.items() if k != "template_variables"}

    return CampaignItemEmitInput(
        tenant_id=tenant_id,
        campaign_id=str(run.campaign_id),
        campaign_version_id=str(run.campaign_version_id),
        run_id=str(run.id),
        run_item_id=str(item.id),
        recipient_id=str(recipient.id),
        intent_key=str(version.intent_key or ""),
        preferred_template_key=version.preferred_template_key,
        channel=version.channel,
        entity_type=str(recipient.entity_type or ""),
        entity_id=str(recipient.entity_id or ""),
        address=str(recipient.address or ""),
        label=recipient.label,
        template_variables=template_variables,
        source_event_id=item.source_event_id,
    )


async def _load_run_graph(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
) -> tuple[
    CommunicationCampaignRun,
    CommunicationCampaignVersion,
    dict[str, CommunicationCampaignRunItem],
    dict[str, CommunicationCampaignRecipient],
]:
    run = await get_run(db, tenant_id=tenant_id, run_id=run_id)
    version = (
        await db.execute(
            select(CommunicationCampaignVersion).where(
                CommunicationCampaignVersion.id == run.campaign_version_id,
                CommunicationCampaignVersion.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if version is None:
        raise CampaignDomainError(
            "version_not_found",
            "CampaignVersion for run not found",
            details={"campaign_version_id": run.campaign_version_id},
        )

    items = (
        await db.execute(
            select(CommunicationCampaignRunItem)
            .options(selectinload(CommunicationCampaignRunItem.recipient))
            .where(CommunicationCampaignRunItem.run_id == str(run.id))
        )
    ).scalars().all()
    item_by_id = {str(i.id): i for i in items}
    recip_by_id = {
        str(i.recipient_id): i.recipient
        for i in items
        if i.recipient is not None
    }
    # Fallback load recipients if relationship not populated.
    if len(recip_by_id) < len(items):
        recipients = (
            await db.execute(
                select(CommunicationCampaignRecipient).where(
                    CommunicationCampaignRecipient.run_id == str(run.id)
                )
            )
        ).scalars().all()
        recip_by_id = {str(r.id): r for r in recipients}

    return run, version, item_by_id, recip_by_id


async def emit_run_item(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    run_item_id: str,
    context: CampaignEmitContext | None = None,
    mode: str = "execute",
    skip_transport: bool = True,
    transport: TransportFn | None = None,
    template_resolver: TemplateResolver | None = None,
    link_resolver: LinkResolver | None = None,
) -> ItemEmitResult:
    """Emit Intent for a single RunItem via the platform Intent path.

    ``mode``:
      - ``request_only`` — build request + mark item emitted (no render/execute)
      - ``render`` — render Command via platform (no persist send)
      - ``execute`` — full ``execute_communication_intent`` (default skip_transport=True)
    """
    mode_norm = str(mode or "execute").strip().lower()
    if mode_norm not in {"request_only", "render", "execute"}:
        raise CampaignDomainError(
            "invalid_emit_mode",
            f"mode must be request_only|render|execute, got {mode!r}",
        )

    run, version, item_by_id, recip_by_id = await _load_run_graph(
        db, tenant_id=tenant_id, run_id=run_id
    )
    item = item_by_id.get(str(run_item_id))
    if item is None:
        raise CampaignDomainError(
            "run_item_not_found",
            "CampaignRunItem not found",
            details={"run_id": run_id, "item_id": run_item_id},
        )

    if str(item.status) == RUN_ITEM_STATUS_EMITTED:
        return ItemEmitResult(
            run_item_id=str(item.id),
            emitted=False,
            intent_request=None,
            skip_reason="already_emitted",
            item_status=RUN_ITEM_STATUS_EMITTED,
        )
    if str(item.status) not in _EMITTABLE:
        return ItemEmitResult(
            run_item_id=str(item.id),
            emitted=False,
            intent_request=None,
            skip_reason=f"status_{item.status}",
            item_status=str(item.status),
        )

    recipient = recip_by_id.get(str(item.recipient_id))
    if recipient is None:
        await mark_run_item_outcome(
            db,
            tenant_id=tenant_id,
            run_id=run_id,
            item_id=str(item.id),
            status=RUN_ITEM_STATUS_FAILED,
            reason_codes=["recipient_missing"],
            reason_message="RunItem has no recipient snapshot row",
        )
        return ItemEmitResult(
            run_item_id=str(item.id),
            emitted=False,
            intent_request=None,
            error_code="recipient_missing",
            item_status=RUN_ITEM_STATUS_FAILED,
        )

    try:
        emit_input = _item_to_input(
            tenant_id=tenant_id,
            run=run,
            version=version,
            item=item,
            recipient=recipient,
        )
        request = build_intent_request(emit_input, context)
    except CampaignDomainError as exc:
        await mark_run_item_outcome(
            db,
            tenant_id=tenant_id,
            run_id=run_id,
            item_id=str(item.id),
            status=RUN_ITEM_STATUS_SKIPPED,
            reason_codes=[exc.code],
            reason_message=exc.message,
        )
        return ItemEmitResult(
            run_item_id=str(item.id),
            emitted=False,
            intent_request=None,
            skip_reason=exc.code,
            error_code=exc.code,
            item_status=RUN_ITEM_STATUS_SKIPPED,
        )

    render_result: IntentRenderResult | None = None
    execute_result: SendCommunicationResult | None = None
    try:
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
    except SendCommunicationError as exc:
        details = getattr(exc, "details", None) or {}
        reason = str(details.get("reason") or "send_failed")
        await mark_run_item_outcome(
            db,
            tenant_id=tenant_id,
            run_id=run_id,
            item_id=str(item.id),
            status=RUN_ITEM_STATUS_FAILED,
            reason_codes=[reason],
            reason_message=str(exc) or reason,
        )
        item.intent_key = str(request.intent)
        item.source_event_id = request.source_event_id
        item.meta = {
            **dict(item.meta or {}),
            "emit_mode": mode_norm,
            "intent_request_snapshot": {
                "intent": str(request.intent),
                "channel": request.channel,
                "automation_identity": request.automation_identity,
            },
        }
        await db.flush()
        return ItemEmitResult(
            run_item_id=str(item.id),
            emitted=False,
            intent_request=request,
            error_code=reason,
            item_status=RUN_ITEM_STATUS_FAILED,
        )
    except Exception as exc:  # noqa: BLE001 — isolate per-item failures
        await mark_run_item_outcome(
            db,
            tenant_id=tenant_id,
            run_id=run_id,
            item_id=str(item.id),
            status=RUN_ITEM_STATUS_FAILED,
            reason_codes=["emit_exception"],
            reason_message=str(exc) or type(exc).__name__,
        )
        return ItemEmitResult(
            run_item_id=str(item.id),
            emitted=False,
            intent_request=request,
            error_code="emit_exception",
            item_status=RUN_ITEM_STATUS_FAILED,
        )

    item.intent_key = str(request.intent)
    item.source_event_id = request.source_event_id
    item.status = RUN_ITEM_STATUS_EMITTED
    item.reason_codes = []
    item.reason_message = None
    item.meta = {
        **dict(item.meta or {}),
        "emit_mode": mode_norm,
        "skip_transport": skip_transport if mode_norm == "execute" else None,
        "intent_request_snapshot": {
            "intent": str(request.intent),
            "channel": request.channel,
            "automation_identity": request.automation_identity,
            "source_event_id": request.source_event_id,
            "preferred_template_key": request.preferred_template_key,
            "recipient_count": len(request.recipients),
            "origin": {
                "entity_type": request.origin.entity_type,
                "entity_id": request.origin.entity_id,
            },
        },
    }
    await db.flush()

    return ItemEmitResult(
        run_item_id=str(item.id),
        emitted=True,
        intent_request=request,
        render_result=render_result,
        execute_result=execute_result,
        item_status=RUN_ITEM_STATUS_EMITTED,
    )


async def emit_run_items(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    run_item_ids: Sequence[str] | None = None,
    context: CampaignEmitContext | None = None,
    mode: str = "execute",
    skip_transport: bool = True,
    transport: TransportFn | None = None,
    template_resolver: TemplateResolver | None = None,
    link_resolver: LinkResolver | None = None,
) -> list[ItemEmitResult]:
    """Emit Intents for many RunItems; failures are isolated per item."""
    _run, _version, item_by_id, _recip = await _load_run_graph(
        db, tenant_id=tenant_id, run_id=run_id
    )
    if run_item_ids is None:
        targets = sorted(item_by_id.keys())
    else:
        targets = [str(i) for i in run_item_ids]

    results: list[ItemEmitResult] = []
    for item_id in targets:
        try:
            results.append(
                await emit_run_item(
                    db,
                    tenant_id=tenant_id,
                    run_id=run_id,
                    run_item_id=item_id,
                    context=context,
                    mode=mode,
                    skip_transport=skip_transport,
                    transport=transport,
                    template_resolver=template_resolver,
                    link_resolver=link_resolver,
                )
            )
        except CampaignDomainError as exc:
            results.append(
                ItemEmitResult(
                    run_item_id=item_id,
                    emitted=False,
                    intent_request=None,
                    error_code=exc.code,
                    skip_reason=exc.code,
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                ItemEmitResult(
                    run_item_id=item_id,
                    emitted=False,
                    intent_request=None,
                    error_code="emit_exception",
                    skip_reason=str(exc) or type(exc).__name__,
                )
            )
    return results


__all__ = [
    "CampaignItemEmitInput",
    "CampaignEmitContext",
    "ItemEmitResult",
    "campaign_identity_for",
    "build_intent_request",
    "emit_run_item",
    "emit_run_items",
]
