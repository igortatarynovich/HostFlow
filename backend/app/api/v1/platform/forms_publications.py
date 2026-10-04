"""ADR-007 Forms platform publication API.

C4 resolve remains a read. FP-2 adds the authenticated publish write:
HTTP → Adapter ``commit_publish`` → ``form_publication_versions``.
FP-4 adds the operator unpublish wrapper: HTTP → Adapter ``deactivate_endpoint``.
Not a second publication write. Not a new serve path.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.trust_role_deps import require_trust_write
from backend.app.db.deps import get_db_with_tenant
from backend.app.forms_platform.adapter import (
    commit_publish,
    deactivate_endpoint,
    resolve_publication,
)
from backend.app.forms_platform.errors import FormsAdapterError, FormsNotFoundError
from backend.app.forms_platform.handlers import list_registered_handlers

router = APIRouter(
    prefix="/platform/forms",
    tags=["forms-platform"],
    redirect_slashes=False,
)


class SubmissionHandlerOut(BaseModel):
    handler_id: str
    module_owner: str
    creates: list[str] = Field(default_factory=list)
    creates_on_create: dict[str, bool] = Field(default_factory=dict)
    route_intent: str


class FormPublicationOut(BaseModel):
    contract_version: str
    adr: str
    publication_id: str
    storage_backend: str
    title: str
    public_slug: Optional[str] = None
    is_active: bool
    lifecycle_status: Optional[str] = None
    published_version: Optional[int] = None
    published_at: Optional[str] = None
    has_immutable_snapshot: Optional[bool] = None
    consent_pin: Optional[dict[str, Any]] = None
    has_field_schema: Optional[bool] = None
    field_schema: Optional[dict[str, Any]] = None
    mode: str
    tier: str
    module_owner: str
    entity_profile_code: str
    presentation_code: Optional[str] = None
    intake_source_profile_id: Optional[str] = None
    operator_state: Optional[str] = None
    public_form_url: Optional[str] = None
    public_intake_path: str
    public_apply_path_template: str
    submission_handler: SubmissionHandlerOut
    capabilities: dict[str, bool] = Field(default_factory=dict)
    canon: Optional[str] = None
    contract_identity: Optional[dict[str, Any]] = None
    routing_status: Optional[str] = None
    routing_reason: Optional[str] = None
    route_intent: Optional[str] = None
    idempotent_replay: Optional[bool] = None
    replayed_version: Optional[int] = None
    replayed_version_id: Optional[str] = None


class FormPublishIn(BaseModel):
    terms_version: Optional[str] = Field(default=None, max_length=64)
    privacy_version: Optional[str] = Field(default=None, max_length=64)
    activate: bool = True
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    field_schema: Optional[dict[str, Any]] = None
    fields: Optional[list[dict[str, Any]]] = None
    presentation_runtime: Optional[dict[str, Any]] = None


class FormHandlersOut(BaseModel):
    handlers: list[SubmissionHandlerOut] = Field(default_factory=list)


async def _presentation_runtime_for_publish(
    db,
    *,
    tenant_id: str,
    form_id: str,
) -> dict[str, Any] | None:
    """Current form field definition to freeze when the operator POST body is empty.

    Presentation leftover is not serve authority (FP-3). At publish it is the
    form's current field subset that ``commit_publish`` freezes into the ledger.
    """
    from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id
    from backend.app.entity_profile.presentation_runtime import (
        FormPresentationNotFoundError,
        resolve_form_presentation_for_intake_source,
    )
    from backend.app.models.intake_routing import IntakeSourceProfile

    profile_id = await resolve_public_intake_source_profile_id(
        db,
        tenant_id=str(tenant_id),
        lead_form_id=str(form_id),
    )
    if not profile_id:
        return None
    profile = await db.get(IntakeSourceProfile, str(profile_id))
    presentation_code = str(getattr(profile, "presentation_code", None) or "").strip()
    if not presentation_code:
        return None
    try:
        runtime = await resolve_form_presentation_for_intake_source(
            db,
            tenant_id=str(tenant_id),
            intake_source_profile_id=str(profile_id),
            presentation_code=presentation_code,
        )
    except FormPresentationNotFoundError:
        return None
    return runtime if isinstance(runtime, dict) else None


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden for tenant")


@router.get("/handlers", response_model=FormHandlersOut)
async def list_forms_platform_handlers(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> FormHandlersOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    rows = list_registered_handlers()
    return FormHandlersOut(handlers=[SubmissionHandlerOut.model_validate(row) for row in rows])


@router.get("/publications/resolve", response_model=FormPublicationOut)
async def resolve_form_publication(
    public_slug: Optional[str] = Query(default=None, min_length=2, max_length=64),
    form_id: Optional[str] = Query(default=None, min_length=1, max_length=36),
    version: Optional[int] = Query(default=None, ge=1),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> FormPublicationOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    if not public_slug and not form_id:
        raise HTTPException(status_code=422, detail="public_slug or form_id is required")

    try:
        publication = await resolve_publication(
            db,
            tenant_id=tenant_id,
            public_slug=public_slug,
            form_id=form_id,
            version=version,
        )
    except FormsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.to_dict()) from exc
    except FormsAdapterError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.to_dict()) from exc
    return FormPublicationOut.model_validate(publication)


@router.post("/{form_id}/publish", response_model=FormPublicationOut)
async def publish_form_publication(
    form_id: str,
    payload: FormPublishIn | None = None,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _role: str = Depends(require_trust_write()),
    idempotency_header: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> FormPublicationOut:
    """Authenticated product write: Adapter commit_publish only."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    body = payload or FormPublishIn()
    idempotency_key = (body.idempotency_key or idempotency_header or "").strip() or None
    presentation_runtime = body.presentation_runtime
    if body.field_schema is None and body.fields is None and presentation_runtime is None:
        presentation_runtime = await _presentation_runtime_for_publish(
            db, tenant_id=tenant_id, form_id=str(form_id).strip()
        )
    try:
        publication = await commit_publish(
            db,
            tenant_id=tenant_id,
            form_id=str(form_id).strip(),
            terms_version=body.terms_version,
            privacy_version=body.privacy_version,
            activate=bool(body.activate),
            idempotency_key=idempotency_key,
            field_schema=body.field_schema,
            fields=body.fields,
            presentation_runtime=presentation_runtime,
        )
        await db.commit()
    except FormsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.to_dict()) from exc
    except FormsAdapterError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.to_dict()) from exc
    return FormPublicationOut.model_validate(publication)


@router.post("/{form_id}/unpublish", response_model=FormPublicationOut)
async def unpublish_form_publication(
    form_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _role: str = Depends(require_trust_write()),
) -> FormPublicationOut:
    """Authenticated lifecycle consume: Adapter deactivate_endpoint only."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        publication = await deactivate_endpoint(
            db,
            tenant_id=tenant_id,
            form_id=str(form_id).strip(),
        )
        await db.commit()
    except FormsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.to_dict()) from exc
    except FormsAdapterError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.to_dict()) from exc
    return FormPublicationOut.model_validate(publication)
