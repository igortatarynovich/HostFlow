from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.schemas.additional_services import (
    ServiceAttachmentCreate,
    ServiceAttachmentOut,
    ServiceCreate,
    ServiceItemCreate,
    ServiceItemDeliverPayload,
    ServiceItemOut,
    ServiceOrderCreate,
    ServiceOrderOut,
    ServiceOrderSummary,
    ServiceOrderUpdate,
    ServiceOut,
    ServiceScheduleCreate,
    ServiceScheduleOut,
    ServiceScheduleUpdate,
    ServiceUpdate,
)
from backend.app.services.additional_services import AdditionalServicesService


router = APIRouter(tags=["additional-services"])


def _svc(db: AsyncSession, tenant_id: UUID) -> AdditionalServicesService:
    return AdditionalServicesService(db, str(tenant_id))


async def _list_service_orders_response(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    candidate_id: Optional[UUID] = None,
    vacancy_id: Optional[UUID] = None,
    company_id: Optional[UUID] = None,
    status: Optional[List[str]] = None,
    q: Optional[str] = None,
    active_own_company_id: Optional[str] = None,
) -> List[ServiceOrderOut]:
    svc = _svc(db, tenant_id)
    rows = await svc.list_orders(
        candidate_id=str(candidate_id) if candidate_id else None,
        vacancy_id=str(vacancy_id) if vacancy_id else None,
        company_id=str(company_id) if company_id else None,
        status=status,
        q=q,
        own_company_scope=active_own_company_id,
    )
    if q and str(q).strip():
        rows = rows[:80]
    return [ServiceOrderOut.model_validate(row, from_attributes=True) for row in rows]


def _ensure_single_owner(
    candidate_id: Optional[str],
    vacancy_id: Optional[str],
    company_id: Optional[str],
) -> None:
    count = sum(1 for value in (candidate_id, vacancy_id, company_id) if value)
    if count != 1:
        raise HTTPException(status_code=422, detail="Exactly one of candidate_id, vacancy_id, company_id must be provided")


@router.get(
    "/services",
    response_model=List[ServiceOut],
    dependencies=[Depends(require_trust_read())],
)
async def list_services(
    include_inactive: bool = Query(False, description="Return inactive catalog items as well"),
    include_metrics: bool = Query(
        False,
        description="Include per-service order counts and revenue from completed orders",
    ),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    rows = await svc.list_services(include_inactive=include_inactive)
    metrics_map = (
        await svc.catalog_usage_metrics_map(own_company_scope=active_own_company_id)
        if include_metrics
        else None
    )
    out: List[ServiceOut] = []
    for row in rows:
        base = ServiceOut.model_validate(row, from_attributes=True)
        if metrics_map is not None:
            oc, rev = metrics_map.get(row.id, (0, Decimal("0")))
            out.append(
                base.model_copy(
                    update={
                        "metrics_orders_count": oc,
                        "metrics_revenue_completed": rev,
                    }
                )
            )
        else:
            out.append(base)
    return out


@router.post(
    "/services",
    response_model=ServiceOut,
    dependencies=[Depends(require_trust_admin())],
)
async def create_service(
    payload: ServiceCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    model = await svc.create_service(payload.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(model)
    return ServiceOut.model_validate(model, from_attributes=True)


@router.patch(
    "/services/{service_id}",
    response_model=ServiceOut,
    dependencies=[Depends(require_trust_admin())],
)
async def update_service(
    service_id: str,
    payload: ServiceUpdate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    model = await svc.get_service(service_id)
    data = payload.model_dump(exclude_unset=True)
    if data:
        model = await svc.update_service(model, data)
        await db.commit()
        await db.refresh(model)
    return ServiceOut.model_validate(model, from_attributes=True)


@router.get(
    "/service-orders",
    response_model=List[ServiceOrderOut],
    dependencies=[Depends(require_trust_read())],
)
async def list_service_orders(
    candidate_id: Optional[UUID] = Query(None),
    vacancy_id: Optional[UUID] = Query(None),
    company_id: Optional[UUID] = Query(None),
    status: Optional[List[str]] = Query(None, description="Filter by status values"),
    q: Optional[str] = Query(None, description="Search order id or notes (substring)"),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    return await _list_service_orders_response(
        db,
        tenant_id,
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
        company_id=company_id,
        status=status,
        q=q,
        active_own_company_id=active_own_company_id,
    )


@router.get(
    "/service-orders/{order_id}",
    response_model=ServiceOrderOut,
    dependencies=[Depends(require_trust_read())],
)
async def get_service_order(
    order_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    order = await svc.get_order(order_id)
    await svc.ensure_order_own_company_scope(order, active_own_company_id)
    return ServiceOrderOut.model_validate(order, from_attributes=True)


@router.get(
    "/candidates/{candidate_id}/service-orders",
    response_model=List[ServiceOrderOut],
    dependencies=[Depends(require_trust_read())],
)
async def list_candidate_service_orders(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    return await _list_service_orders_response(
        db,
        tenant_id,
        candidate_id=candidate_id,
        vacancy_id=None,
        company_id=None,
        status=None,
        q=None,
        active_own_company_id=active_own_company_id,
    )


@router.post(
    "/service-orders",
    response_model=ServiceOrderOut,
    dependencies=[Depends(require_trust_write())],
)
async def create_service_order(
    payload: ServiceOrderCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)

    if not payload.items:
        raise HTTPException(status_code=422, detail="At least one item must be provided")

    candidate_id = (payload.candidate_id or None) and str(payload.candidate_id)
    vacancy_id = (payload.vacancy_id or None) and str(payload.vacancy_id)
    company_id = (payload.company_id or None) and str(payload.company_id)
    _ensure_single_owner(candidate_id, vacancy_id, company_id)

    order_payload = payload.model_dump(exclude={"items"}, exclude_none=True)
    order_payload["candidate_id"] = candidate_id
    order_payload["vacancy_id"] = vacancy_id
    order_payload["company_id"] = company_id
    order_payload["requested_by"] = payload.requested_by or current_user.sub
    resolved_oc = await svc.resolve_new_order_own_company_id(
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
        company_id=company_id,
        active_own_company_id=active_own_company_id,
    )
    if resolved_oc:
        order_payload["own_company_id"] = resolved_oc

    items_payload = [item.model_dump(exclude_unset=True) for item in payload.items]

    order = await svc.create_order(order_payload, items_payload)
    try:
        from backend.app.services import uos_auto_activities

        await uos_auto_activities.ensure_service_order_confirm_task(db, str(tenant_id), str(current_user.sub), order)
    except Exception:
        pass
    await db.commit()
    order = await svc.get_order(order.id)
    return ServiceOrderOut.model_validate(order, from_attributes=True)


@router.patch(
    "/service-orders/{order_id}",
    response_model=ServiceOrderOut,
    dependencies=[Depends(require_trust_write())],
)
async def patch_service_order(
    order_id: str,
    payload: ServiceOrderUpdate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    order = await svc.get_order(order_id)
    await svc.ensure_order_own_company_scope(order, active_own_company_id)
    data = payload.model_dump(exclude_unset=True)

    status_value = data.pop("status", None)
    if status_value is not None:
        order = await svc.set_order_status(order, status_value)

    if data:
        order = await svc.update_order(order, data)

    await db.commit()
    order = await svc.get_order(order_id)
    return ServiceOrderOut.model_validate(order, from_attributes=True)


@router.post(
    "/service-orders/{order_id}/items",
    response_model=ServiceItemOut,
    dependencies=[Depends(require_trust_write())],
)
async def add_service_item(
    order_id: str,
    payload: ServiceItemCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    order = await svc.get_order(order_id)
    await svc.ensure_order_own_company_scope(order, active_own_company_id)
    item = await svc.add_item(order, payload.model_dump(exclude_unset=True))
    await db.commit()
    item = await svc.get_item(item.id)
    return ServiceItemOut.model_validate(item, from_attributes=True)


@router.post(
    "/service-items/{item_id}/schedule",
    response_model=ServiceScheduleOut,
    dependencies=[Depends(require_trust_write())],
)
async def add_service_schedule(
    item_id: str,
    payload: ServiceScheduleCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    await svc.ensure_item_branch_scope(str(item_id), active_own_company_id)
    item = await svc.get_item(item_id)
    schedule = await svc.add_schedule(item, payload.model_dump(exclude_unset=True))
    await db.commit()
    schedule = await svc.get_schedule(schedule.id)
    return ServiceScheduleOut.model_validate(schedule, from_attributes=True)


@router.patch(
    "/service-schedule/{schedule_id}",
    response_model=ServiceScheduleOut,
    dependencies=[Depends(require_trust_write())],
)
async def patch_service_schedule(
    schedule_id: str,
    payload: ServiceScheduleUpdate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    await svc.ensure_schedule_branch_scope(str(schedule_id), active_own_company_id)
    schedule = await svc.get_schedule(schedule_id)
    data = payload.model_dump(exclude_unset=True)
    if data:
        schedule = await svc.update_schedule(schedule, data)
        await db.commit()
        schedule = await svc.get_schedule(schedule_id)
    return ServiceScheduleOut.model_validate(schedule, from_attributes=True)


@router.post(
    "/service-items/{item_id}/attachments",
    response_model=ServiceAttachmentOut,
    dependencies=[Depends(require_trust_write())],
)
async def add_service_attachment(
    item_id: str,
    payload: ServiceAttachmentCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    await svc.ensure_item_branch_scope(str(item_id), active_own_company_id)
    item = await svc.get_item(item_id, with_relations=False)
    attachment = await svc.add_attachment(item, payload.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(attachment)
    return ServiceAttachmentOut.model_validate(attachment, from_attributes=True)


@router.post(
    "/service-items/{item_id}/deliver",
    response_model=ServiceItemOut,
    dependencies=[Depends(require_trust_write())],
)
async def deliver_service_item(
    item_id: str,
    payload: ServiceItemDeliverPayload = Body(...),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    await svc.ensure_item_branch_scope(str(item_id), active_own_company_id)
    item = await svc.get_item(item_id)
    attachments_payload = [att.model_dump(exclude_unset=True) for att in payload.attachments]
    result_document_payload = (
        payload.result_document.model_dump(exclude_unset=True)
        if payload.result_document
        else None
    )
    meta_payload = payload.meta or {}
    updated = await svc.deliver_item(
        item,
        status=payload.status,
        result_document=result_document_payload,
        attachments=attachments_payload,
        meta=meta_payload,
    )
    await db.commit()
    updated = await svc.get_item(updated.id)
    return ServiceItemOut.model_validate(updated, from_attributes=True)


@router.get(
    "/service-orders/{order_id}/summary",
    response_model=ServiceOrderSummary,
    dependencies=[Depends(require_trust_read())],
)
async def get_service_order_summary(
    order_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    svc = _svc(db, tenant_id)
    order = await svc.get_order(order_id)
    await svc.ensure_order_own_company_scope(order, active_own_company_id)
    data = await svc.summary_for_order(order)
    order_out = ServiceOrderOut.model_validate(data["order"], from_attributes=True)
    blocking_items = [
        ServiceItemOut.model_validate(item, from_attributes=True)
        for item in data.get("blocking_items", [])
    ]
    summary = ServiceOrderSummary(
        order=order_out,
        blocking_items=blocking_items,
        missing_documents=data.get("missing_documents", {}),
    )
    return summary
