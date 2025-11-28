from __future__ import annotations

import json
from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.public.intake import _load_candidate_by_token  # type: ignore
from backend.app.db.deps import get_db_with_tenant
from backend.app.db.session import async_session_maker
from backend.app.schemas.scanner import (
    ScanSessionCreatePublic,
    ScanSessionSchema,
    ScanPresetSchema,
)
from backend.app.services.scanner import (
    create_scan_session,
    get_scan_session as load_scan_session,
    get_scan_session_by_id,
    process_scan_session,
    serialize_scan_session,
    upload_scan_page,
)
from backend.app.services.scanner_presets import list_presets

router = APIRouter(prefix="/public/scan-sessions", tags=["public-scan"])
meta_router = APIRouter(prefix="/public/scan", tags=["public-scan"])


@meta_router.get("/presets", response_model=list[ScanPresetSchema])
async def list_public_presets() -> list[ScanPresetSchema]:
    return [ScanPresetSchema(**preset.__dict__) for preset in list_presets()]


@router.post("", response_model=ScanSessionSchema)
async def create_public_scan_session(
    payload: ScanSessionCreatePublic,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> ScanSessionSchema:
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, payload.token)
    preset_code = payload.preset_code or payload.document_type
    session = await create_scan_session(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate.id,
        document_type=payload.document_type,
        preset_code=preset_code,
        document_kind_id=payload.document_kind_id,
        expected_pages=payload.expected_pages,
        meta=payload.meta,
    )
    return ScanSessionSchema(**serialize_scan_session(session))


@router.get("", response_model=None)
async def get_public_scan_sessions_root():
    """Handle GET requests to /public/scan-sessions without ID - redirect to frontend"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        content='<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url=/public/scan"><script>window.location.href="/public/scan";</script></head><body>Redirecting to <a href="/public/scan">/public/scan</a>...</body></html>',
        status_code=200
    )


@router.get("/{session_id}", response_model=ScanSessionSchema)
async def get_public_scan_session(
    session_id: str,
) -> ScanSessionSchema:
    # For public endpoints, load session first to get tenant_id, then use it
    async with async_session_maker() as db:
        # Load session without RLS by using direct query
        from sqlalchemy import text
        # First, get tenant_id from session without RLS
        result = await db.execute(
            text("SELECT tenant_id FROM scan_sessions WHERE id = :session_id"),
            {"session_id": session_id}
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="scan_session_not_found")
        tenant_id = UUID(row[0])
        # Set tenant context for RLS
        try:
            await db.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
                {"tenant_id": str(tenant_id)},
            )
        except Exception:
            pass
        # Now load session with RLS
        session = await get_scan_session_by_id(db, session_id=session_id)
        return ScanSessionSchema(**serialize_scan_session(session))


@router.post("/{session_id}/pages", response_model=ScanSessionSchema)
async def upload_public_scan_page(
    session_id: str,
    file: UploadFile = File(...),
    page_code: str = Form(...),
    rotation: int = Form(0),
    filter_name: str | None = Form(None),
    meta: str | None = Form(None),
) -> ScanSessionSchema:
    async with async_session_maker() as db:
        # Load tenant_id first without RLS
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT tenant_id FROM scan_sessions WHERE id = :session_id"),
            {"session_id": session_id}
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="scan_session_not_found")
        tenant_id = UUID(row[0])
        # Set tenant context for RLS
        try:
            await db.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
                {"tenant_id": str(tenant_id)},
            )
        except Exception:
            pass
        
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
        await db.commit()
        return ScanSessionSchema(**serialize_scan_session(session))


@router.post("/{session_id}/process", response_model=ScanSessionSchema)
async def process_public_scan_session(
    session_id: str,
) -> ScanSessionSchema:
    async with async_session_maker() as db:
        # Load tenant_id first without RLS
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT tenant_id FROM scan_sessions WHERE id = :session_id"),
            {"session_id": session_id}
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="scan_session_not_found")
        tenant_id = UUID(row[0])
        # Set tenant context for RLS
        try:
            await db.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
                {"tenant_id": str(tenant_id)},
            )
        except Exception:
            pass
        session = await process_scan_session(db, tenant_id=tenant_id, session_id=session_id)
        await db.commit()
        return ScanSessionSchema(**serialize_scan_session(session))

