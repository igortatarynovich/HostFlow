from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.db.meta_leads_tenant_dep import (
    ensure_token_matches_header_tenant as _ensure_tenant,
    get_db_with_meta_leads_effective_tenant,
)
from backend.app.modules.leads import admin_service
from backend.app.api.v1.utils.own_company import resolve_own_company_id_for_session
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.own_company import OwnCompany
from backend.app.models.user import User
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

SUPPORTED_COMPANY_INTAKE_LANGUAGES = {"pl", "en", "ru"}
COMPANY_INTAKE_FORM_TYPE = "company_intake"


class CompanyIntakeSourceProfileOut(BaseModel):
    id: str
    name: str
    tenant_id: str
    own_company_id: str
    own_company_name: str | None = None
    public_slug: str
    public_url_path: str
    lead_type: str
    lead_target_type: str
    form_type: str
    source: str
    default_language: str
    supported_languages: list[str]
    default_assignee_id: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class CompanyIntakeSourceProfileCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    own_company_id: str = Field(..., min_length=1, max_length=36)
    public_slug: str = Field(..., min_length=2, max_length=64)
    source: str = Field(default="website", max_length=64)
    default_language: str = Field(default="pl", max_length=8)
    supported_languages: list[str] = Field(default_factory=lambda: ["pl", "en", "ru"])
    default_assignee_id: str | None = Field(default=None, max_length=36)
    is_active: bool = True

    @field_validator("public_slug")
    @classmethod
    def _normalize_slug(cls, value: str) -> str:
        cleaned = value.strip().lower()
        import re

        cleaned = re.sub(r"[^a-z0-9-]+", "-", cleaned)
        cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
        if len(cleaned) < 2:
            raise ValueError("public_slug is too short")
        return cleaned

    @field_validator("source")
    @classmethod
    def _normalize_source(cls, value: str) -> str:
        cleaned = value.strip().lower().replace("-", "_")
        if cleaned in {"meta", "facebook", "instagram", "fb", "ig"}:
            return "meta_ads"
        return cleaned or "website"

    @field_validator("default_language")
    @classmethod
    def _normalize_default_language(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in SUPPORTED_COMPANY_INTAKE_LANGUAGES:
            raise ValueError("default_language must be one of pl, en, ru")
        return cleaned

    @field_validator("supported_languages")
    @classmethod
    def _normalize_supported_languages(cls, value: list[str]) -> list[str]:
        out: list[str] = []
        for item in value or []:
            cleaned = str(item or "").strip().lower()
            if cleaned in SUPPORTED_COMPANY_INTAKE_LANGUAGES and cleaned not in out:
                out.append(cleaned)
        return out or ["pl", "en", "ru"]


class CompanyIntakeSourceProfilePatchIn(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    own_company_id: str | None = Field(default=None, max_length=36)
    public_slug: str | None = Field(default=None, min_length=2, max_length=64)
    source: str | None = Field(default=None, max_length=64)
    default_language: str | None = Field(default=None, max_length=8)
    supported_languages: list[str] | None = None
    default_assignee_id: str | None = Field(default=None, max_length=36)
    is_active: bool | None = None

    _normalize_slug = field_validator("public_slug")(CompanyIntakeSourceProfileCreateIn._normalize_slug.__func__)  # type: ignore[attr-defined]
    _normalize_source = field_validator("source")(CompanyIntakeSourceProfileCreateIn._normalize_source.__func__)  # type: ignore[attr-defined]
    _normalize_default_language = field_validator("default_language")(CompanyIntakeSourceProfileCreateIn._normalize_default_language.__func__)  # type: ignore[attr-defined]
    _normalize_supported_languages = field_validator("supported_languages")(CompanyIntakeSourceProfileCreateIn._normalize_supported_languages.__func__)  # type: ignore[attr-defined]


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


def _company_intake_public_path(public_slug: str) -> str:
    return f"/forms/company-intake/{public_slug}"


def _languages_to_storage(values: list[str]) -> str:
    out: list[str] = []
    for value in values:
        cleaned = str(value or "").strip().lower()
        if cleaned in SUPPORTED_COMPANY_INTAKE_LANGUAGES and cleaned not in out:
            out.append(cleaned)
    return ",".join(out or ["pl", "en", "ru"])


def _languages_from_storage(raw: str | None) -> list[str]:
    if not raw:
        return ["pl", "en", "ru"]
    out: list[str] = []
    for item in str(raw).split(","):
        cleaned = item.strip().lower()
        if cleaned in SUPPORTED_COMPANY_INTAKE_LANGUAGES and cleaned not in out:
            out.append(cleaned)
    return out or ["pl", "en", "ru"]


async def _ensure_own_company_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
) -> OwnCompany:
    oc = str(own_company_id or "").strip()
    row = await db.scalar(
        select(OwnCompany).where(
            OwnCompany.tenant_id == tenant_id,
            OwnCompany.id == oc,
            OwnCompany.is_archived.is_(False),
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "own_company_invalid", "message": "Owner company is invalid for this workspace."},
        )
    return row


async def _ensure_assignee_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str | None,
) -> str | None:
    uid = str(user_id or "").strip() or None
    if not uid:
        return None
    row = await db.scalar(
        select(User.id).where(
            User.tenant_id == tenant_id,
            User.id == uid,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "default_manager_invalid", "message": "Default manager is invalid for this workspace."},
        )
    return str(row)


async def _ensure_company_intake_slug_available(
    db: AsyncSession,
    *,
    public_slug: str,
    exclude_profile_id: str | None = None,
) -> None:
    stmt = select(IntakeSourceProfile.id).where(IntakeSourceProfile.public_slug == public_slug)
    if exclude_profile_id:
        stmt = stmt.where(IntakeSourceProfile.id != exclude_profile_id)
    existing = await db.scalar(stmt.limit(1))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "company_intake_slug_taken", "message": "This public slug is already used."},
        )


def _company_intake_source_out(
    row: IntakeSourceProfile,
    *,
    own_company_name: str | None = None,
) -> CompanyIntakeSourceProfileOut:
    slug = str(row.public_slug or "").strip()
    return CompanyIntakeSourceProfileOut(
        id=str(row.id),
        name=row.name,
        tenant_id=str(row.tenant_id),
        own_company_id=str(row.own_company_id),
        own_company_name=own_company_name,
        public_slug=slug,
        public_url_path=_company_intake_public_path(slug),
        lead_type=row.lead_type or "client",
        lead_target_type=row.lead_target_type or "client_lead",
        form_type=row.form_type or COMPANY_INTAKE_FORM_TYPE,
        source=row.source or "website",
        default_language=row.default_language or "pl",
        supported_languages=_languages_from_storage(row.supported_languages),
        default_assignee_id=row.default_assignee_id,
        is_active=bool(row.is_active),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get(
    "/company-intake-source-profiles",
    response_model=list[CompanyIntakeSourceProfileOut],
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def list_company_intake_source_profiles_endpoint(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> list[CompanyIntakeSourceProfileOut]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    rows = (
        await db.execute(
            select(IntakeSourceProfile, OwnCompany.name)
            .join(OwnCompany, OwnCompany.id == IntakeSourceProfile.own_company_id)
            .where(
                IntakeSourceProfile.tenant_id == tenant_id,
                IntakeSourceProfile.form_type == COMPANY_INTAKE_FORM_TYPE,
                IntakeSourceProfile.lead_type == "client",
                IntakeSourceProfile.lead_target_type == "client_lead",
            )
            .order_by(IntakeSourceProfile.created_at.asc())
        )
    ).all()
    return [_company_intake_source_out(row, own_company_name=own_name) for row, own_name in rows]


@router.post(
    "/company-intake-source-profiles",
    response_model=CompanyIntakeSourceProfileOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def create_company_intake_source_profile_endpoint(
    payload: CompanyIntakeSourceProfileCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> CompanyIntakeSourceProfileOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    own_company = await _ensure_own_company_for_tenant(
        db, tenant_id=tenant_id, own_company_id=payload.own_company_id
    )
    default_assignee_id = await _ensure_assignee_for_tenant(
        db, tenant_id=tenant_id, user_id=payload.default_assignee_id
    )
    await _ensure_company_intake_slug_available(db, public_slug=payload.public_slug)
    row = IntakeSourceProfile(
        tenant_id=tenant_id,
        code=f"company-intake-{payload.public_slug}",
        name=payload.name.strip(),
        provider="public_intake",
        channel="public_form",
        own_company_id=payload.own_company_id.strip(),
        route_intent="sales_inquiry",
        public_slug=payload.public_slug,
        form_type=COMPANY_INTAKE_FORM_TYPE,
        lead_type="client",
        lead_target_type="client_lead",
        source=payload.source,
        default_language=payload.default_language,
        supported_languages=_languages_to_storage(payload.supported_languages),
        default_assignee_id=default_assignee_id,
        is_active=payload.is_active,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _company_intake_source_out(row, own_company_name=own_company.name)


@router.patch(
    "/company-intake-source-profiles/{profile_id}",
    response_model=CompanyIntakeSourceProfileOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def patch_company_intake_source_profile_endpoint(
    profile_id: str,
    payload: CompanyIntakeSourceProfilePatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> CompanyIntakeSourceProfileOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    row = await db.scalar(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.tenant_id == tenant_id,
            IntakeSourceProfile.id == profile_id,
            IntakeSourceProfile.form_type == COMPANY_INTAKE_FORM_TYPE,
            IntakeSourceProfile.lead_type == "client",
            IntakeSourceProfile.lead_target_type == "client_lead",
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company intake source profile not found")

    patch = payload.model_dump(exclude_unset=True)
    if "name" in patch and patch["name"] is not None:
        row.name = str(patch["name"]).strip() or row.name
    if "own_company_id" in patch and patch["own_company_id"] is not None:
        own_company = await _ensure_own_company_for_tenant(
            db, tenant_id=tenant_id, own_company_id=str(patch["own_company_id"])
        )
        row.own_company_id = own_company.id
    else:
        own_company = await db.get(OwnCompany, row.own_company_id)
    if "public_slug" in patch and patch["public_slug"] is not None:
        next_slug = str(patch["public_slug"]).strip()
        if next_slug != row.public_slug:
            await _ensure_company_intake_slug_available(
                db, public_slug=next_slug, exclude_profile_id=str(row.id)
            )
            row.public_slug = next_slug
            row.code = f"company-intake-{next_slug}"
    if "source" in patch and patch["source"] is not None:
        row.source = str(patch["source"]).strip().lower() or "website"
    if "default_language" in patch and patch["default_language"] is not None:
        row.default_language = str(patch["default_language"]).strip().lower() or "pl"
    if "supported_languages" in patch and patch["supported_languages"] is not None:
        row.supported_languages = _languages_to_storage(patch["supported_languages"])
    if "default_assignee_id" in patch:
        row.default_assignee_id = await _ensure_assignee_for_tenant(
            db, tenant_id=tenant_id, user_id=patch["default_assignee_id"]
        )
    if "is_active" in patch and patch["is_active"] is not None:
        row.is_active = bool(patch["is_active"])
    await db.commit()
    await db.refresh(row)
    return _company_intake_source_out(row, own_company_name=getattr(own_company, "name", None))


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
