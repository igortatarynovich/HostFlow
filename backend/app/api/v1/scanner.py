from __future__ import annotations

import json
from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.schemas.scanner import (
    ScanAttachResponse,
    ScanPageSchema,
    ScanSessionCreateInternal,
    ScanSessionSchema,
    ScanPresetSchema,
)
from backend.app.services.scanner import (
    attach_scan_session,
    create_scan_session,
    process_scan_session,
    serialize_scan_session,
    upload_scan_page,
    get_scan_session as load_scan_session,
)
from backend.app.services.scanner_presets import list_presets

router = APIRouter(prefix="/api/v1/scan-sessions", tags=["scan-sessions"])
meta_router = APIRouter(prefix="/api/v1/scan", tags=["scan-presets"])


@meta_router.get("/presets", response_model=list[ScanPresetSchema])
async def list_scan_presets() -> list[ScanPresetSchema]:
    return [ScanPresetSchema(**preset.__dict__) for preset in list_presets()]


@router.post("", response_model=ScanSessionSchema)
async def create_scan_session_api(
    payload: ScanSessionCreateInternal,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ScanSessionSchema:
    db, tenant_id = db_tenant
    session = await create_scan_session(
        db,
        tenant_id=tenant_id,
        candidate_id=payload.candidate_id,
        document_type=payload.document_type,
        preset_code=payload.preset_code,
        document_kind_id=payload.document_kind_id,
        expected_pages=payload.expected_pages,
        meta=payload.meta,
    )
    return ScanSessionSchema(**serialize_scan_session(session))


@router.get("/{session_id}", response_model=ScanSessionSchema)
async def get_scan_session_api(
    session_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ScanSessionSchema:
    db, tenant_id = db_tenant
    session = await load_scan_session(db, tenant_id=tenant_id, session_id=session_id)
    return ScanSessionSchema(**serialize_scan_session(session))


@router.post("/{session_id}/pages", response_model=ScanSessionSchema)
async def upload_scan_page_api(
    session_id: str,
    file: UploadFile = File(...),
    page_code: str = Form(...),
    rotation: int = Form(0),
    filter_name: str | None = Form(None),
    meta: str | None = Form(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ScanSessionSchema:
    db, tenant_id = db_tenant
    meta_payload = None
    if meta:
        try:
            meta_payload = json.loads(meta)
        except Exception:
            raise HTTPException(status_code=422, detail="invalid_meta_json")
    session = await upload_scan_page(
        db,
        tenant_id=tenant_id,
        session_id=session_id,
        page_code=page_code,
        upload=file,
        rotation=rotation,
        applied_filter=filter_name,
        meta=meta_payload,
    )
    return ScanSessionSchema(**serialize_scan_session(session))


@router.post("/{session_id}/process", response_model=ScanSessionSchema)
async def process_scan_session_api(
    session_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ScanSessionSchema:
    db, tenant_id = db_tenant
    session = await process_scan_session(db, tenant_id=tenant_id, session_id=session_id)
    return ScanSessionSchema(**serialize_scan_session(session))


@router.post("/{session_id}/attach", response_model=ScanAttachResponse)
async def attach_scan_session_api(
    session_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ScanAttachResponse:
    db, tenant_id = db_tenant
    payload = await attach_scan_session(
        db,
        tenant_id=tenant_id,
        session_id=session_id,
        uploaded_by=current_user.email,
    )
    return ScanAttachResponse(**payload)
