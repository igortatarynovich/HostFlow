from __future__ import annotations

from typing import List, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.leads import admin_service
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id
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
    MetaIncomingLeadsPreviewResponse,
    MetaLeadResponse,
    MetaLeadRetryRequest,
    MetaLeadRetryResponse,
    MetaLeadRerouteRequest,
    MetaLeadSettingsOut,
    MetaLeadSettingsUpdate,
    UnmappedLeadsResponse,
)
from backend.app.services.imports import leads as import_service


router = APIRouter(prefix="/leads", tags=["settings-leads"])


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for tenant")


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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaLeadSettingsOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    return await admin_service.get_settings(db, tenant_id)


@router.patch(
    "/settings",
    response_model=MetaLeadSettingsOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def update_settings_endpoint(
    payload: MetaLeadSettingsUpdate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaLeadSettingsOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    result = await admin_service.update_settings(db, tenant_id, payload)
    await db.commit()
    return result


@router.get(
    "/meta/incoming-preview",
    response_model=MetaIncomingLeadsPreviewResponse,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def meta_incoming_preview_endpoint(
    limit: int = Query(default=25, ge=1, le=50, description="Max recent Meta leads to return"),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaIncomingLeadsPreviewResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    return await admin_service.list_meta_incoming_preview(db, tenant_id, limit=limit)


@router.get(
    "/credentials",
    response_model=list[MetaCredentialOut],
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def list_credentials_endpoint(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> list[MetaCredentialOut]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaCredentialOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaCredentialOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> Response:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaCredentialRotateResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> list[MetaAdsMapEntry]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaAdsMapEntry:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaAdsMapEntry:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> Response:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> UnmappedLeadsResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaLeadResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    own_company_id: str = Depends(resolve_active_own_company_id),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaLeadRetryResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
