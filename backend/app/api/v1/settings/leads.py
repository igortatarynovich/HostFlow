from __future__ import annotations

from typing import List, Literal, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.db.meta_leads_tenant_dep import (
    ensure_token_matches_header_tenant as _ensure_tenant,
    get_db_with_meta_leads_effective_tenant,
)
from backend.app.modules.leads import admin_service
from backend.app.api.v1.utils.own_company import resolve_own_company_id_for_session
from backend.app.modules.leads.schemas import (
    LeadImportJobListResponse,
    LeadImportJobOut,
    MetaAdsMapCreate,
    MetaAdsMapEntry,
    MetaAdsMapUpdate,
    MetaCredentialCreate,
    MetaCredentialOut,
    MetaCredentialRotateResponse,
    MetaCredentialUpdate,
    GenericInboundWebhookRotateResponse,
    MetaGraphFieldDataPreviewRequest,
    MetaGraphFieldDataPreviewResponse,
    MetaIncomingLeadsPreviewResponse,
    MetaLeadFormListResponse,
    MetaLeadFormMappingOut,
    MetaLeadFormMappingUpdate,
    MetaFormRouteOut,
    MetaFormRouteUpdate,
    MetaLeadResponse,
    MetaLeadRetryRequest,
    MetaLeadRetryResponse,
    MetaLeadRerouteRequest,
    MetaLeadSelfServeOnboardingOut,
    MetaLeadSettingsOut,
    MetaLeadSettingsUpdate,
    MetaOAuthCompleteIn,
    MetaOAuthCompleteOut,
    MetaOAuthFinalizeIn,
    MetaOAuthFinalizeOut,
    MetaOAuthStartOut,
    LeadMessageTemplateOut,
    LeadMessageTemplateCreateUpdate,
    UnmappedLeadsResponse,
)
from backend.app.services.imports import leads as import_service


router = APIRouter(prefix="/leads", tags=["settings-leads"])


def _serialize_job(job) -> LeadImportJobOut:
    return LeadImportJobOut(
        id=UUID(job.id),
        filename=job.filename,
        status=job.status,  # type: ignore[arg-type]
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        success_rows=job.success_rows,
        duplicate_rows=job.duplicate_rows,
        failed_rows=job.failed_rows,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_report=list(job.error_report or []),
    )


@router.get(
    "/settings",
    response_model=MetaLeadSettingsOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def get_settings_endpoint(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaLeadSettingsOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    out = await admin_service.get_settings(db, tenant_id)
    return await admin_service.enrich_meta_leads_tenant_context(db, header_tid, tenant_id, out)


@router.get(
    "/meta/self-serve-onboarding",
    response_model=MetaLeadSelfServeOnboardingOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def meta_self_serve_onboarding_endpoint(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaLeadSelfServeOnboardingOut:
    """Public app id, webhook URL, permissions — so tenants connect Meta without operator (see env META_LEADS_*)."""
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    include_secret = ctx.role == Role.administrator.value
    out = await admin_service.get_meta_self_serve_onboarding(
        db, tenant_id, include_shared_app_secret=include_secret
    )
    return await admin_service.enrich_meta_leads_tenant_context(db, header_tid, tenant_id, out)


@router.post(
    "/meta/oauth/start",
    response_model=MetaOAuthStartOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def meta_oauth_start_endpoint(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaOAuthStartOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    return await admin_service.meta_oauth_start(db, tenant_id, ctx.sub)


@router.post(
    "/meta/oauth/complete",
    response_model=MetaOAuthCompleteOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def meta_oauth_complete_endpoint(
    payload: MetaOAuthCompleteIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaOAuthCompleteOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.meta_oauth_complete(db, tenant_id, ctx.sub, payload)
    await db.commit()
    return result


@router.post(
    "/meta/oauth/finalize",
    response_model=MetaOAuthFinalizeOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def meta_oauth_finalize_endpoint(
    payload: MetaOAuthFinalizeIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaOAuthFinalizeOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.meta_oauth_finalize(db, tenant_id, ctx.sub, payload)
    await db.commit()
    return result


@router.patch(
    "/settings",
    response_model=MetaLeadSettingsOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def update_settings_endpoint(
    payload: MetaLeadSettingsUpdate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaLeadSettingsOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.update_settings(db, tenant_id, payload)
    await db.commit()
    return await admin_service.enrich_meta_leads_tenant_context(db, header_tid, tenant_id, result)


@router.get(
    "/message-templates",
    response_model=list[LeadMessageTemplateOut],
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def list_lead_message_templates_endpoint(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> list[LeadMessageTemplateOut]:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    return await admin_service.list_lead_message_templates(db, str(tenant_uuid))


@router.post(
    "/message-templates",
    response_model=LeadMessageTemplateOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def create_lead_message_template_endpoint(
    payload: LeadMessageTemplateCreateUpdate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> LeadMessageTemplateOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    out = await admin_service.create_lead_message_template(db, str(tenant_uuid), payload)
    await db.commit()
    return out


@router.patch(
    "/message-templates/{template_id}",
    response_model=LeadMessageTemplateOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def update_lead_message_template_endpoint(
    template_id: str,
    payload: LeadMessageTemplateCreateUpdate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> LeadMessageTemplateOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    out = await admin_service.update_lead_message_template(db, str(tenant_uuid), template_id, payload)
    await db.commit()
    return out


@router.delete(
    "/message-templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def delete_lead_message_template_endpoint(
    template_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> Response:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    deleted = await admin_service.delete_lead_message_template(db, str(tenant_uuid), template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/inbound-webhook/rotate",
    response_model=GenericInboundWebhookRotateResponse,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def rotate_generic_inbound_webhook_endpoint(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> GenericInboundWebhookRotateResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    result = await admin_service.rotate_generic_inbound_webhook_secret(db, tenant_id)
    await db.commit()
    return result


@router.get(
    "/meta/incoming-preview",
    response_model=MetaIncomingLeadsPreviewResponse,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def meta_incoming_preview_endpoint(
    limit: int = Query(default=25, ge=1, le=50, description="Max recent leads to return"),
    source: Literal["meta", "webhook"] = Query(
        "meta",
        description="Lead.source filter: meta (default) or webhook (§2.11 generic inbound)",
    ),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaIncomingLeadsPreviewResponse:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    return await admin_service.list_meta_incoming_preview(db, tenant_id, limit=limit, source=source)


@router.get(
    "/meta/forms",
    response_model=MetaLeadFormListResponse,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def meta_lead_forms_list_endpoint(
    source: Literal["meta", "webhook"] = Query("meta"),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaLeadFormListResponse:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    return await admin_service.list_meta_lead_forms(db, tenant_id, source=source)


@router.get(
    "/meta/forms/{form_id}/mapping",
    response_model=MetaLeadFormMappingOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def meta_lead_form_mapping_get_endpoint(
    form_id: str,
    page_id: Optional[str] = Query(default=None),
    source: Literal["meta", "webhook"] = Query("meta"),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaLeadFormMappingOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    return await admin_service.get_meta_lead_form_mapping(
        db, tenant_id, form_id, page_id=page_id, source=source
    )


@router.put(
    "/meta/forms/{form_id}/mapping",
    response_model=MetaLeadFormMappingOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def meta_lead_form_mapping_put_endpoint(
    form_id: str,
    payload: MetaLeadFormMappingUpdate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaLeadFormMappingOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.upsert_meta_lead_form_mapping(
        db, tenant_id, form_id, payload, user_sub=ctx.sub
    )
    await db.commit()
    return result


@router.get(
    "/meta/forms/{form_id}/route",
    response_model=MetaFormRouteOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def meta_form_route_get_endpoint(
    form_id: str,
    page_id: Optional[str] = Query(default=None),
    source: Literal["meta", "webhook"] = Query("meta"),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaFormRouteOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    return await admin_service.get_meta_form_route(
        db, tenant_id, form_id, page_id=page_id, source=source
    )


@router.put(
    "/meta/forms/{form_id}/route",
    response_model=MetaFormRouteOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def meta_form_route_put_endpoint(
    form_id: str,
    payload: MetaFormRouteUpdate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaFormRouteOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.upsert_meta_form_route(
        db, tenant_id, form_id, payload, user_sub=ctx.sub
    )
    await db.commit()
    return result


@router.post(
    "/meta/graph-field-preview",
    response_model=MetaGraphFieldDataPreviewResponse,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def meta_graph_field_preview_endpoint(
    payload: MetaGraphFieldDataPreviewRequest,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaGraphFieldDataPreviewResponse:
    """Fetch real Meta lead field_data from Graph for field-mapping (Page token from credentials)."""
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    return await admin_service.fetch_meta_graph_field_preview(db, tenant_id, payload)


@router.get(
    "/credentials",
    response_model=list[MetaCredentialOut],
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def list_credentials_endpoint(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> list[MetaCredentialOut]:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    return await admin_service.list_credentials(db, tenant_id)


@router.post(
    "/credentials",
    response_model=MetaCredentialOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def create_credential_endpoint(
    payload: MetaCredentialCreate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaCredentialOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.create_credential(db, tenant_id, payload)
    await db.commit()
    return result


@router.patch(
    "/credentials/{credential_id}",
    response_model=MetaCredentialOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def update_credential_endpoint(
    credential_id: UUID,
    payload: MetaCredentialUpdate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaCredentialOut:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.update_credential(db, tenant_id, str(credential_id), payload)
    await db.commit()
    return result


@router.delete(
    "/credentials/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def delete_credential_endpoint(
    credential_id: UUID,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> Response:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    await admin_service.delete_credential(db, tenant_id, str(credential_id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/credentials/{credential_id}/rotate",
    response_model=MetaCredentialRotateResponse,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def rotate_credential_endpoint(
    credential_id: UUID,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaCredentialRotateResponse:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.rotate_credential(db, tenant_id, str(credential_id))
    await db.commit()
    return result


@router.get(
    "/mapping",
    response_model=list[MetaAdsMapEntry],
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def list_mapping_endpoint(
    search: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> list[MetaAdsMapEntry]:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    return await admin_service.list_mapping(db, tenant_id, search, limit)


@router.post(
    "/mapping",
    response_model=MetaAdsMapEntry,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def create_mapping_endpoint(
    payload: MetaAdsMapCreate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaAdsMapEntry:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.upsert_mapping(db, tenant_id, payload)
    await db.commit()
    return result


@router.patch(
    "/mapping/{ad_id}",
    response_model=MetaAdsMapEntry,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def update_mapping_endpoint(
    ad_id: int,
    payload: MetaAdsMapUpdate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaAdsMapEntry:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.upsert_mapping(db, tenant_id, payload, ad_id=ad_id)
    await db.commit()
    return result


@router.delete(
    "/mapping/{ad_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def delete_mapping_endpoint(
    ad_id: int,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> Response:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    await admin_service.delete_mapping(db, tenant_id, ad_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/unmapped-leads",
    response_model=UnmappedLeadsResponse,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def list_unmapped_leads_endpoint(
    status: str = Query(default="needs_routing", description="Lead status to filter"),
    limit_per_ad: int = Query(default=10, ge=1, le=50, description="Max leads per ad_id group"),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> UnmappedLeadsResponse:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    return await admin_service.list_unmapped_leads(
        db,
        tenant_id=tenant_id,
        status=status,
        limit_per_ad=limit_per_ad,
    )


@router.post(
    "/leads/{lead_id}/reroute",
    response_model=MetaLeadResponse,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def reroute_lead_endpoint(
    lead_id: UUID,
    payload: MetaLeadRerouteRequest,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaLeadResponse:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    result = await admin_service.reroute_lead(db, tenant_id, str(lead_id), payload)
    return result


@router.post(
    "/leads/retry",
    response_model=MetaLeadRetryResponse,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def retry_leads_endpoint(
    payload: MetaLeadRetryRequest,
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: str | None = Header(default=None, alias="X-Own-Company-Id"),
    db_tenant: Tuple[AsyncSession, UUID, str] = Depends(get_db_with_meta_leads_effective_tenant),
) -> MetaLeadRetryResponse:
    db, tenant_uuid, header_tid = db_tenant
    _ensure_tenant(ctx, header_tid)
    tenant_id = str(tenant_uuid)
    own_company_id = await resolve_own_company_id_for_session(
        db, tenant_id, ctx, x_own_company_id
    )
    result = await admin_service.retry_leads(db, tenant_id, own_company_id, payload)
    await db.commit()
    return result


@router.post(
    "/import",
    response_model=LeadImportJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def import_leads_csv(
    file: UploadFile = File(...),
    sync: bool = Query(False, description="Run import synchronously for diagnostics"),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> LeadImportJobOut:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="EMPTY_FILE")

    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    filename = file.filename or "leads.csv"

    job = await import_service.create_import_job(
        db,
        tenant_id=tenant_id,
        created_by=ctx.sub,
        filename=filename,
    )
    await db.commit()

    if sync:
        await import_service.run_import_job(
            job.id,
            tenant_id=tenant_id,
            created_by=ctx.sub,
            filename=filename,
            content=content,
        )
    else:
        import_service.enqueue_import_job(
            job.id,
            tenant_id=tenant_id,
            created_by=ctx.sub,
            filename=filename,
            content=content,
        )

    await db.refresh(job)
    return _serialize_job(job)


@router.get(
    "/import/{job_id}",
    response_model=LeadImportJobOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def get_import_job(
    job_id: UUID,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> LeadImportJobOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)

    job = await import_service.get_import_job(db, tenant_id=tenant_id, job_id=str(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
    return _serialize_job(job)


@router.get(
    "/import",
    response_model=LeadImportJobListResponse,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def list_import_jobs_endpoint(
    limit: int = Query(20, ge=1, le=100),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> LeadImportJobListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)

    jobs = await import_service.list_import_jobs(db, tenant_id=tenant_id, limit=limit)
    items: List[LeadImportJobOut] = [_serialize_job(job) for job in jobs]
    return LeadImportJobListResponse(items=items)
