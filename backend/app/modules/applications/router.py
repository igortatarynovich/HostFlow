from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_read, require_trust_write
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.applications import mutations
from backend.app.modules.applications.mappers import (
    lead_to_recruitment_application,
    sales_inquiry_to_application,
)
from backend.app.modules.applications.listing import (
    count_recruitment_inbox,
    list_recruitment_inbox_leads,
    normalize_recruitment_inbox_scope,
    normalize_recruitment_inbox_tab,
    recruitment_inbox_tab_counts,
)
from backend.app.modules.applications.sales_resolve import (
    list_sales_inquiry_pairs,
    resolve_sales_inquiry_and_lead,
)
from backend.app.models import Lead
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.applications.schemas import (
    ApplicationAssignIn,
    ApplicationFollowUpIn,
    ApplicationIntakeDecisionIn,
    ApplicationListResponse,
    ApplicationOut,
    ApplicationProcessResult,
    ApplicationStagePatch,
    ApplicationVacancyConfirmIn,
    SalesCapabilitySpineOut,
    SalesInquiryDuplicateHintOut,
    SalesInquiryDuplicateListResponse,
)
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id

sales_router = APIRouter(prefix="/sales/inquiries", tags=["sales-inquiries"])
recruitment_router = APIRouter(prefix="/recruitment/applications", tags=["recruitment-applications"])


async def _resolve_sales_or_404(
    db: AsyncSession,
    tenant_id: str,
    application_id: str,
    own_company_id: str,
) -> tuple[SalesInquiry, Lead]:
    """Resolve SalesInquiry + transport Lead by SI id or Lead id."""
    try:
        inquiry, lead = await resolve_sales_inquiry_and_lead(
            db,
            tenant_id=tenant_id,
            application_id=application_id,
            ensure_if_lead=True,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found") from exc
    lead_oc = str(getattr(lead, "own_company_id", "") or "")
    inquiry_oc = str(getattr(inquiry, "own_company_id", "") or "")
    if own_company_id:
        if lead_oc and lead_oc != str(own_company_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        if inquiry_oc and inquiry_oc != str(own_company_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return inquiry, lead


@sales_router.get("", response_model=ApplicationListResponse)
@sales_router.get("/", response_model=ApplicationListResponse, include_in_schema=False)
async def list_sales_inquiries(
    limit: int = Query(200, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_trust_read()),
) -> ApplicationListResponse:
    db, tenant_id = db_tenant
    pairs, total = await list_sales_inquiry_pairs(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        limit=limit,
        offset=offset,
    )
    items = [sales_inquiry_to_application(inquiry, lead) for inquiry, lead in pairs]
    return ApplicationListResponse(items=items, total=total)


@sales_router.get("/{application_id}", response_model=ApplicationOut)
async def get_sales_inquiry(
    application_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_trust_read()),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations._reload_sales(db, str(tenant_id), own_company_id, application_id)


@sales_router.get(
    "/{application_id}/capability-spine",
    response_model=SalesCapabilitySpineOut,
)
async def get_sales_inquiry_capability_spine(
    application_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_trust_read()),
) -> SalesCapabilitySpineOut:
    """Display-only Pipeline v1 spine: Capability / Review / Convert / Traceability.

    Does not match, resolve review, convert, or invent Capability decisions.
    """
    from backend.app.modules.sales.services.capability_spine_read import (
        get_capability_spine_for_application,
    )

    db, tenant_id = db_tenant
    inquiry, _lead = await _resolve_sales_or_404(
        db, str(tenant_id), application_id, own_company_id
    )
    payload = await get_capability_spine_for_application(
        db,
        tenant_id=str(tenant_id),
        application_id=str(inquiry.id),
    )
    return SalesCapabilitySpineOut.model_validate(payload)


@sales_router.get(
    "/{application_id}/possible-duplicates",
    response_model=SalesInquiryDuplicateListResponse,
)
async def list_sales_inquiry_possible_duplicates(
    application_id: str,
    limit: int = Query(10, ge=1, le=20),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_trust_read()),
) -> SalesInquiryDuplicateListResponse:
    """Sibling client inquiries sharing phone and/or email (operator duplicate hint)."""
    from backend.app.modules.applications.sales_inquiry_duplicates import (
        find_possible_duplicate_sales_inquiries,
    )

    db, tenant_id = db_tenant
    _inquiry, lead = await _resolve_sales_or_404(
        db, str(tenant_id), application_id, own_company_id
    )
    hits = await find_possible_duplicate_sales_inquiries(
        db,
        tenant_id=str(tenant_id),
        lead=lead,
        own_company_id=own_company_id,
        limit=limit,
    )
    items = [
        SalesInquiryDuplicateHintOut(application=app, match_reason=reason)
        for app, reason in hits
    ]
    return SalesInquiryDuplicateListResponse(items=items, total=len(items))


@sales_router.patch("/{application_id}", response_model=ApplicationOut)
async def patch_sales_inquiry(
    application_id: str,
    payload: ApplicationStagePatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_trust_write()),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations.patch_sales_stage(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )


@sales_router.post("/{application_id}/convert-client", response_model=ApplicationOut)
async def convert_sales_inquiry(
    application_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_trust_write()),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations.convert_sales_inquiry(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        application_id=application_id,
        current_user=current_user,
    )


@recruitment_router.get("", response_model=ApplicationListResponse)
@recruitment_router.get("/", response_model=ApplicationListResponse, include_in_schema=False)
async def list_recruitment_applications(
    vacancy_id: str | None = Query(None, description="Filter open applications for a search/vacancy"),
    scope: str = Query(
        "all",
        description="Inbox scope: all (open + completed + rejected) or open (pending only)",
    ),
    tab: str | None = Query(None, description="Inbox tab bucket: all, new, in_progress, completed"),
    include_counts: bool = Query(False, description="Include per-tab totals for badge counts"),
    limit: int = Query(200, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_trust_read()),
) -> ApplicationListResponse:
    db, tenant_id = db_tenant
    inbox_scope = normalize_recruitment_inbox_scope(scope)
    inbox_tab = normalize_recruitment_inbox_tab(tab)
    vacancy_filter = str(vacancy_id or "").strip() or None
    lead_rows = await list_recruitment_inbox_leads(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        tab=inbox_tab,
        scope=inbox_scope,
        vacancy_id=vacancy_filter,
        limit=limit,
        offset=offset,
        order_updated_at=(inbox_tab == "completed"),
    )
    items = [lead_to_recruitment_application(row) for row in lead_rows]
    total = await count_recruitment_inbox(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        tab=inbox_tab,
        scope=inbox_scope,
        vacancy_id=vacancy_filter,
    )
    counts = None
    if include_counts and offset == 0 and inbox_scope == "all":
        counts = await recruitment_inbox_tab_counts(
            db,
            tenant_id=str(tenant_id),
            own_company_id=own_company_id,
            vacancy_id=vacancy_filter,
        )
    return ApplicationListResponse(items=items, total=total, counts=counts)


@recruitment_router.get("/{application_id}", response_model=ApplicationOut)
async def get_recruitment_application(
    application_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _role: str = Depends(require_trust_read()),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations._reload_recruitment(db, str(tenant_id), application_id)


@recruitment_router.patch("/{application_id}", response_model=ApplicationOut)
async def patch_recruitment_application(
    application_id: str,
    payload: ApplicationStagePatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_trust_write()),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations.patch_recruitment_stage(
        db,
        tenant_id=str(tenant_id),
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )


@recruitment_router.post("/{application_id}/intake-decision", response_model=ApplicationOut)
async def recruitment_application_intake_decision(
    application_id: str,
    payload: ApplicationIntakeDecisionIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_trust_write()),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations.recruitment_intake_decision(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )


@recruitment_router.post("/{application_id}/confirm-vacancy", response_model=ApplicationOut)
async def recruitment_application_confirm_vacancy(
    application_id: str,
    payload: ApplicationVacancyConfirmIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_trust_write()),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations.recruitment_confirm_vacancy(
        db,
        tenant_id=str(tenant_id),
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )


@recruitment_router.post("/{application_id}/process", response_model=ApplicationProcessResult)
async def recruitment_application_process(
    application_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_trust_write()),
) -> ApplicationProcessResult:
    db, tenant_id = db_tenant
    return await mutations.recruitment_process_application(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        application_id=application_id,
        current_user=current_user,
    )


@recruitment_router.post("/{application_id}/follow-up", response_model=ApplicationOut)
async def recruitment_application_follow_up(
    application_id: str,
    payload: ApplicationFollowUpIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_trust_write()),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations.recruitment_follow_up(
        db,
        tenant_id=str(tenant_id),
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )


@recruitment_router.post("/{application_id}/assign", response_model=ApplicationOut)
async def recruitment_application_assign(
    application_id: str,
    payload: ApplicationAssignIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_trust_write()),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations.recruitment_assign(
        db,
        tenant_id=str(tenant_id),
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )
