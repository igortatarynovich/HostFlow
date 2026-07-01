from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models import WorkforceEmployee
from backend.app.services.document_merge import (
    create_template,
    delete_template,
    generate_merge_document,
    get_template,
    list_templates,
    update_template,
)

router = APIRouter(prefix="/document-merge", tags=["document-merge"])

TEMPLATE_ADMIN_ROLES = (
    Role.administrator,
    Role.supervisor,
    Role.compliance_officer,
)
GENERATE_ROLES = (
    Role.recruiter,
    Role.manager,
    Role.admin,
    Role.compliance_officer,
    Role.hr_officer,
)


class MergeTemplateOut(BaseModel):
    id: str
    tenant_id: str
    own_company_id: Optional[str] = None
    code: str
    name: str
    description: Optional[str] = None
    body_text: str
    output_mime: str
    variable_bindings: Optional[Dict[str, Any]] = None
    output_filename_pattern: Optional[str] = None
    doc_type: str
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class MergeTemplateCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    body_text: str = Field(..., min_length=1)
    output_mime: str = Field(default="text/plain", max_length=128)
    variable_bindings: Optional[Dict[str, Any]] = None
    output_filename_pattern: Optional[str] = Field(default=None, max_length=512)
    doc_type: str = Field(default="additional_document", max_length=128)
    own_company_id: Optional[str] = None
    is_active: bool = True


class MergeTemplatePatch(BaseModel):
    code: Optional[str] = Field(default=None, max_length=128)
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    body_text: Optional[str] = None
    output_mime: Optional[str] = Field(default=None, max_length=128)
    variable_bindings: Optional[Dict[str, Any]] = None
    output_filename_pattern: Optional[str] = Field(default=None, max_length=512)
    doc_type: Optional[str] = Field(default=None, max_length=128)
    own_company_id: Optional[str] = None
    is_active: Optional[bool] = None


class MergeGenerateIn(BaseModel):
    template_id: Optional[str] = None
    template_code: Optional[str] = None
    candidate_id: Optional[UUID] = None
    workforce_employee_id: Optional[UUID] = None
    variable_bindings: Optional[Dict[str, Any]] = None


class MergeGenerateOut(BaseModel):
    log_id: str
    document_id: str
    template_id: Optional[str] = None
    status: str


def _to_out(row: Any) -> MergeTemplateOut:
    return MergeTemplateOut(
        id=row.id,
        tenant_id=row.tenant_id,
        own_company_id=row.own_company_id,
        code=row.code,
        name=row.name,
        description=row.description,
        body_text=row.body_text,
        output_mime=row.output_mime,
        variable_bindings=row.variable_bindings,
        output_filename_pattern=row.output_filename_pattern,
        doc_type=row.doc_type,
        is_active=bool(row.is_active),
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


@router.get(
    "/templates",
    response_model=List[MergeTemplateOut],
    dependencies=[Depends(require_roles(*TEMPLATE_ADMIN_ROLES))],
)
async def api_list_merge_templates(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    include_inactive: bool = Query(False),
    own_company_id: Optional[str] = Query(None),
):
    db, tenant_id = db_tenant
    rows = await list_templates(
        db,
        str(tenant_id),
        include_inactive=include_inactive,
        own_company_id=own_company_id,
    )
    return [_to_out(r) for r in rows]


@router.post(
    "/templates",
    response_model=MergeTemplateOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*TEMPLATE_ADMIN_ROLES))],
)
async def api_create_merge_template(
    payload: MergeTemplateCreate,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    try:
        row = await create_template(db, str(tenant_id), payload.model_dump())
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(row)


@router.get(
    "/templates/{template_id}",
    response_model=MergeTemplateOut,
    dependencies=[Depends(require_roles(*TEMPLATE_ADMIN_ROLES))],
)
async def api_get_merge_template(
    template_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    row = await get_template(db, str(tenant_id), template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="template_not_found")
    return _to_out(row)


@router.patch(
    "/templates/{template_id}",
    response_model=MergeTemplateOut,
    dependencies=[Depends(require_roles(*TEMPLATE_ADMIN_ROLES))],
)
async def api_patch_merge_template(
    template_id: str,
    payload: MergeTemplatePatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    data = payload.model_dump(exclude_unset=True)
    try:
        row = await update_template(db, str(tenant_id), template_id, data)
        if row is None:
            raise HTTPException(status_code=404, detail="template_not_found")
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(row)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None,
    dependencies=[Depends(require_roles(*TEMPLATE_ADMIN_ROLES))],
)
async def api_delete_merge_template(
    template_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    ok = await delete_template(db, str(tenant_id), template_id)
    if not ok:
        raise HTTPException(status_code=404, detail="template_not_found")
    await db.commit()
    return None


@router.post(
    "/generate",
    response_model=MergeGenerateOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GENERATE_ROLES))],
)
async def api_generate_merge_document(
    payload: MergeGenerateIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    if not payload.template_id and not (payload.template_code and payload.template_code.strip()):
        raise HTTPException(status_code=422, detail="template_id_or_template_code_required")

    cand_uuid = str(payload.candidate_id) if payload.candidate_id else None
    emp_uuid = str(payload.workforce_employee_id) if payload.workforce_employee_id else None

    if cand_uuid:
        await ensure_candidate_access(db, tid, cand_uuid, current_user)
    if emp_uuid:
        emp_row = await db.get(WorkforceEmployee, emp_uuid)
        if not emp_row or emp_row.tenant_id != tid:
            raise HTTPException(status_code=404, detail="workforce_employee_not_found")
        if emp_row.candidate_id:
            await ensure_candidate_access(db, tid, str(emp_row.candidate_id), current_user)

    uid = getattr(current_user, "sub", None) or getattr(current_user, "user_id", None)

    try:
        log, doc = await generate_merge_document(
            db,
            tid,
            template_id=payload.template_id,
            template_code=payload.template_code.strip() if payload.template_code else None,
            candidate_id=cand_uuid,
            workforce_employee_id=emp_uuid,
            variable_bindings=payload.variable_bindings,
            triggered_by_user_id=str(uid) if uid else None,
        )
        await db.commit()
    except ValueError as ve:
        await db.rollback()
        code = str(ve)
        if code == "template_not_found":
            raise HTTPException(status_code=404, detail=code) from ve
        if code in (
            "candidate_not_found",
            "workforce_employee_not_found",
            "candidate_or_employee_required",
            "candidate_required_for_document",
        ):
            raise HTTPException(status_code=422, detail=code) from ve
        if code.startswith("TRUSTED_IDENTITY_"):
            raise HTTPException(status_code=422, detail={"code": code}) from ve
        raise HTTPException(status_code=400, detail=code) from ve
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return MergeGenerateOut(
        log_id=log.id,
        document_id=str(doc.id),
        template_id=log.template_id,
        status=log.status,
    )
