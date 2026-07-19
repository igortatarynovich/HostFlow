"""Forms P2.5 — Builder HTTP adapter (thin Catalog + draft client).

No publish, themes, analytics, or intake mapping.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.forms_platform.builder.composition import (
    FormDraftComposition,
    parse_composition,
)
from backend.app.forms_platform.builder.draft_persistence import (
    BUILDER_DRAFT_PERSISTENCE_CONTRACT,
    archive_draft,
    create_draft,
    get_draft,
    update_draft,
)
from backend.app.forms_platform.builder.read_model import BuilderReadModel
from backend.app.forms_platform.errors import (
    FormsAdapterError,
    FormsBuilderDraftConflictError,
    FormsBuilderDraftNotFoundError,
)
from backend.app.forms_platform.field_catalog import (
    bootstrap_platform_standard_library,
    platform_registry,
)
from backend.app.models.tenant_lead_form import TenantLeadForm

router = APIRouter(
    prefix="/platform/forms/builder",
    tags=["forms-builder"],
    redirect_slashes=False,
)


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden for tenant")


def _http_from_forms_error(exc: FormsAdapterError) -> HTTPException:
    return HTTPException(
        status_code=int(exc.http_status),
        detail={"error": exc.code, "message": exc.message, "details": exc.details},
    )


def _read_model() -> BuilderReadModel:
    bootstrap_platform_standard_library()
    return BuilderReadModel(platform_registry())


def draft_id_for_form(form_id: str) -> str:
    return f"form:{str(form_id).strip()}"


async def _require_form(
    session: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> TenantLeadForm:
    row = await session.scalar(
        select(TenantLeadForm).where(
            TenantLeadForm.tenant_id == tenant_id,
            TenantLeadForm.id == form_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Lead form not found")
    return row


class PaletteItemOut(BaseModel):
    component_id: str
    component_version: str
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    label_key: Optional[str] = None
    icon: Optional[str] = None
    supports_preview: bool = False


class PaletteOut(BaseModel):
    contract: str = "forms.builder.read_model.v1"
    items: list[PaletteItemOut] = Field(default_factory=list)


class ComponentViewOut(BaseModel):
    component_id: str
    component_version: str
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    label_key: Optional[str] = None
    icon: Optional[str] = None
    supports_preview: bool = False
    config_fields: list[dict[str, Any]] = Field(default_factory=list)


class DraftOut(BaseModel):
    contract: str = BUILDER_DRAFT_PERSISTENCE_CONTRACT
    tenant_id: str
    draft_id: str
    form_id: Optional[str] = None
    revision: int
    status: str
    composition_contract: str
    composition: dict[str, Any]
    exists: bool = True


class DraftSaveIn(BaseModel):
    composition: dict[str, Any]
    expected_revision: Optional[int] = None


@router.get("/palette", response_model=PaletteOut)
async def builder_palette(
    query: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.administrator, Role.supervisor)),
) -> PaletteOut:
    _db, tenant_uuid = db_tenant
    _ensure_tenant(ctx, str(tenant_uuid))
    rm = _read_model()
    items = rm.list_palette(query=query, category=category)
    return PaletteOut(
        items=[
            PaletteItemOut(
                component_id=i.component_id,
                component_version=i.component_version,
                category=i.category,
                tags=list(i.tags),
                label_key=i.label_key,
                icon=i.icon,
                supports_preview=i.supports_preview,
            )
            for i in items
        ]
    )


@router.get("/components/{component_id}", response_model=ComponentViewOut)
async def builder_component_view(
    component_id: str,
    version: str = Query(..., description="Pinned component_version"),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.administrator, Role.supervisor)),
) -> ComponentViewOut:
    _db, tenant_uuid = db_tenant
    _ensure_tenant(ctx, str(tenant_uuid))
    rm = _read_model()
    try:
        view = rm.get_component(component_id, version)
    except FormsAdapterError as exc:
        raise _http_from_forms_error(exc) from exc
    return ComponentViewOut(
        component_id=view.component_id,
        component_version=view.component_version,
        category=view.category,
        tags=list(view.tags),
        label_key=view.label_key,
        icon=view.icon,
        supports_preview=view.supports_preview,
        config_fields=[f.to_dict() for f in view.config_fields],
    )


@router.get("/forms/{form_id}/draft", response_model=DraftOut)
async def get_form_builder_draft(
    form_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.administrator, Role.supervisor)),
) -> DraftOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    await _require_form(db, tenant_id=tenant_id, form_id=form_id)
    did = draft_id_for_form(form_id)
    try:
        record = await get_draft(db, tenant_id=tenant_id, draft_id=did)
    except FormsBuilderDraftNotFoundError:
        empty = FormDraftComposition(draft_id=did, instances=())
        return DraftOut(
            tenant_id=tenant_id,
            draft_id=did,
            form_id=form_id,
            revision=0,
            status="active",
            composition_contract=empty.contract,
            composition=empty.to_dict(),
            exists=False,
        )
    except FormsAdapterError as exc:
        raise _http_from_forms_error(exc) from exc
    return DraftOut(
        tenant_id=record.tenant_id,
        draft_id=record.draft_id,
        form_id=record.form_id or form_id,
        revision=record.revision,
        status=record.status,
        composition_contract=record.composition_contract,
        composition=record.composition,
        exists=True,
    )


@router.put("/forms/{form_id}/draft", response_model=DraftOut)
async def save_form_builder_draft(
    form_id: str,
    body: DraftSaveIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.administrator)),
) -> DraftOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    await _require_form(db, tenant_id=tenant_id, form_id=form_id)
    did = draft_id_for_form(form_id)
    bootstrap_platform_standard_library()
    registry = platform_registry()
    try:
        raw = dict(body.composition or {})
        raw["draft_id"] = did
        composition = parse_composition(raw)
        if composition.draft_id != did:
            raise HTTPException(status_code=422, detail="composition.draft_id must match form draft")
        try:
            existing = await get_draft(db, tenant_id=tenant_id, draft_id=did)
        except FormsBuilderDraftNotFoundError:
            existing = None
        if existing is None:
            record = await create_draft(
                db,
                tenant_id=tenant_id,
                composition=composition,
                form_id=form_id,
                registry=registry,
                require_valid=True,
            )
        else:
            expected = body.expected_revision
            if expected is None:
                raise HTTPException(
                    status_code=422,
                    detail="expected_revision is required when updating an existing draft",
                )
            record = await update_draft(
                db,
                tenant_id=tenant_id,
                draft_id=did,
                composition=composition,
                expected_revision=int(expected),
                registry=registry,
                require_valid=True,
            )
        await db.commit()
    except FormsBuilderDraftConflictError as exc:
        await db.rollback()
        raise _http_from_forms_error(exc) from exc
    except FormsAdapterError as exc:
        await db.rollback()
        raise _http_from_forms_error(exc) from exc
    return DraftOut(
        tenant_id=record.tenant_id,
        draft_id=record.draft_id,
        form_id=record.form_id or form_id,
        revision=record.revision,
        status=record.status,
        composition_contract=record.composition_contract,
        composition=record.composition,
        exists=True,
    )


@router.post("/forms/{form_id}/draft/archive", response_model=DraftOut)
async def archive_form_builder_draft(
    form_id: str,
    expected_revision: int = Query(...),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.administrator)),
) -> DraftOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    await _require_form(db, tenant_id=tenant_id, form_id=form_id)
    did = draft_id_for_form(form_id)
    try:
        record = await archive_draft(
            db,
            tenant_id=tenant_id,
            draft_id=did,
            expected_revision=expected_revision,
        )
        await db.commit()
    except FormsAdapterError as exc:
        await db.rollback()
        raise _http_from_forms_error(exc) from exc
    return DraftOut(
        tenant_id=record.tenant_id,
        draft_id=record.draft_id,
        form_id=record.form_id or form_id,
        revision=record.revision,
        status=record.status,
        composition_contract=record.composition_contract,
        composition=record.composition,
        exists=True,
    )
