"""HTTP surface for the RODO obligations ops projection.

Queue / retry / exempt over canonical ``compliance_state``. Not a second
state-machine: does not write closed states itself and has no mark-resolved.
"""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.trust_role_deps import require_trust_read, require_trust_write
from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.leads.schemas import (
    LeadRodoExemptRequest,
    LeadRodoOpsQueueItemOut,
    LeadRodoOpsQueueResponse,
)
from backend.app.services.lead_rodo_obligation import (
    COMPLIANCE_OPEN_STATES,
    ComplianceTransitionError,
)

router = APIRouter()


@router.get(
    "/compliance/rodo/queue",
    response_model=LeadRodoOpsQueueResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_trust_read())],
)
async def list_rodo_obligation_queue(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    state: str | None = Query(
        None,
        description="Open compliance_state filter: delivery_required | review_required | delivery_failed.",
    ),
    sla_breached: bool = Query(False, description="Only items past SLA due_at."),
    escalated: bool = Query(False, description="Only SMTP-exhausted escalations."),
    include_terminal: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> LeadRodoOpsQueueResponse:
    from backend.app.services.lead_rodo_ops import list_open_obligations

    db, tenant_uuid = db_tenant
    states = None
    if state is not None and str(state).strip():
        token = str(state).strip().lower()
        if token not in COMPLIANCE_OPEN_STATES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="state must be an open compliance_state",
            )
        states = (token,)
    queue = await list_open_obligations(
        db,
        tenant_id=str(tenant_uuid),
        states=states,
        include_terminal=include_terminal,
        sla_breached_only=sla_breached,
        escalated_only=escalated,
        limit=limit,
        offset=offset,
    )
    return LeadRodoOpsQueueResponse(
        items=[LeadRodoOpsQueueItemOut.model_validate(i.to_dict()) for i in queue.items],
        total=queue.total,
        counts=queue.counts,
        sla_breached=queue.sla_breached,
        escalated=queue.escalated,
        limit=queue.limit,
        offset=queue.offset,
    )


@router.post(
    "/{lead_id}/compliance/rodo/retry",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_trust_write())],
)
async def retry_lead_rodo_obligation(
    lead_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict:
    from backend.app.modules.leads import crud
    from backend.app.services.lead_rodo_ops import retry_open_obligation_send

    db, tenant_uuid = db_tenant
    tenant_id_str = str(tenant_uuid)
    lead = await crud.get_lead(db, tenant_id=tenant_id_str, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    try:
        ok, msg = await retry_open_obligation_send(
            db,
            tenant_id=tenant_id_str,
            lead=lead,
            actor_id=str(current_user.sub or "").strip() or None,
        )
    except ComplianceTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    if not ok:
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    await db.commit()
    return {"ok": True, "message": msg}


@router.post(
    "/{lead_id}/compliance/rodo/exempt",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_trust_write())],
)
async def exempt_lead_rodo_obligation(
    lead_id: str,
    body: LeadRodoExemptRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict:
    """Operator exempt with a lawful reason code. Not mark-resolved."""
    from backend.app.modules.leads import crud
    from backend.app.services.audit import log_audit_event
    from backend.app.services.lead_rodo import mark_lead_rodo_exempt

    db, tenant_uuid = db_tenant
    tenant_id_str = str(tenant_uuid)
    lead = await crud.get_lead(db, tenant_id=tenant_id_str, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    actor = str(current_user.sub or "").strip() or None
    try:
        mark_lead_rodo_exempt(
            lead,
            exemption_code=body.exemption_code,
            actor_id=actor,
            note=body.note,
        )
    except ComplianceTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    await log_audit_event(
        db,
        tenant_id=tenant_id_str,
        event_type=AuditEventType.rodo_exempted,
        entity_type=AuditEntityType.lead,
        entity_id=str(lead.id),
        actor_id=actor,
        payload={"exemption_code": body.exemption_code},
    )
    await db.commit()
    return {"ok": True}
