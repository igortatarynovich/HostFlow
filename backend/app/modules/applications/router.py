from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.applications import mutations
from backend.app.modules.applications.mappers import (
    lead_to_recruitment_application,
    lead_to_sales_inquiry,
)
from backend.app.modules.applications.listing import (
    count_recruitment_inbox,
    list_recruitment_inbox_leads,
    normalize_recruitment_inbox_scope,
    normalize_recruitment_inbox_tab,
    recruitment_inbox_tab_counts,
)
from backend.app.modules.applications.schemas import (
    ApplicationAssignIn,
    ApplicationFollowUpIn,
    ApplicationIntakeDecisionIn,
    ApplicationListResponse,
    ApplicationOut,
    ApplicationProcessResult,
    ApplicationStagePatch,
    ApplicationVacancyConfirmIn,
    SalesInquiryDuplicateHintOut,
    SalesInquiryDuplicateListResponse,
)
from backend.app.modules.leads import crud, service
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id

sales_router = APIRouter(prefix="/sales/inquiries", tags=["sales-inquiries"])
recruitment_router = APIRouter(prefix="/recruitment/applications", tags=["recruitment-applications"])


async def _get_lead_or_404(db: AsyncSession, tenant_id: str, application_id: str):
    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return lead


@sales_router.get("", response_model=ApplicationListResponse)
@sales_router.get("/", response_model=ApplicationListResponse, include_in_schema=False)
async def list_sales_inquiries(
    limit: int = Query(200, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> ApplicationListResponse:
    db, tenant_id = db_tenant
    result = await service.list_leads(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        lead_type="client",
        lead_target_type="client_lead",
        limit=limit,
        offset=offset,
    )
    items = [lead_to_sales_inquiry(row) for row in result.items]
    return ApplicationListResponse(items=items, total=result.total)


@sales_router.get("/{application_id}", response_model=ApplicationOut)
async def get_sales_inquiry(
    application_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations._reload_sales(db, str(tenant_id), own_company_id, application_id)


@sales_router.get(
    "/{application_id}/possible-duplicates",
    response_model=SalesInquiryDuplicateListResponse,
)
async def list_sales_inquiry_possible_duplicates(
    application_id: str,
    limit: int = Query(10, ge=1, le=20),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> SalesInquiryDuplicateListResponse:
    """Sibling client inquiries sharing phone and/or email (operator duplicate hint)."""
    from backend.app.modules.applications.sales_inquiry_duplicates import (
        find_possible_duplicate_sales_inquiries,
    )

    db, tenant_id = db_tenant
    lead = await _get_lead_or_404(db, str(tenant_id), application_id)
    if str(getattr(lead, "lead_type", "") or "").lower() != "client":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if own_company_id and str(getattr(lead, "own_company_id", "") or "") not in ("", str(own_company_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
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
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
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
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
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
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
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
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations._reload_recruitment(db, str(tenant_id), application_id)


@recruitment_router.patch("/{application_id}", response_model=ApplicationOut)
async def patch_recruitment_application(
    application_id: str,
    payload: ApplicationStagePatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
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
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
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
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
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
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
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
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
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
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
) -> ApplicationOut:
    db, tenant_id = db_tenant
    return await mutations.recruitment_assign(
        db,
        tenant_id=str(tenant_id),
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )
