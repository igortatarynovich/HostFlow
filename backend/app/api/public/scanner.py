from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.public.intake import _load_candidate_by_token, _save_public_document_upload  # type: ignore
from backend.app.api.public.intake_tenant_bind import bind_session_for_intake_token
from backend.app.db.deps import get_db
from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.scan import ScanSession
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
from backend.app.services.candidate_telegram_notifications import (
    send_candidate_documents_progress_telegram,
    sync_candidate_ready_for_handoff_gate,
)

router = APIRouter(prefix="/public/scan-sessions", tags=["public-scan"])
meta_router = APIRouter(prefix="/public/scan", tags=["public-scan"])


@meta_router.get("/presets", response_model=list[ScanPresetSchema])
async def list_public_presets() -> list[ScanPresetSchema]:
    return [ScanPresetSchema(**preset.__dict__) for preset in list_presets()]


@router.post("", response_model=ScanSessionSchema)
async def create_public_scan_session(
    payload: ScanSessionCreatePublic,
    db: AsyncSession = Depends(get_db),
) -> ScanSessionSchema:
    tenant_id = await bind_session_for_intake_token(db, payload.token)
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


@router.post("/{session_id}/pdf", response_model=ScanSessionSchema)
async def upload_public_scan_pdf(
    session_id: str,
    file: UploadFile = File(...),
    meta: str | None = Form(None),
) -> ScanSessionSchema:
    async with async_session_maker() as db:
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT tenant_id FROM scan_sessions WHERE id = :session_id"),
            {"session_id": session_id},
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="scan_session_not_found")
        tenant_id = UUID(row[0])
        try:
            await db.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
                {"tenant_id": str(tenant_id)},
            )
        except Exception:
            pass

        session = await get_scan_session_by_id(db, session_id=session_id, for_update=True)
        if session.attached_at:
            raise HTTPException(status_code=409, detail="session_already_attached")
        candidate = await db.scalar(
            select(Candidate)
            .where(
                Candidate.id == session.candidate_id,
                Candidate.tenant_id == str(tenant_id),
                Candidate.deleted_at.is_(None),
            )
            .limit(1)
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="candidate_not_found")

        meta_payload = {}
        if meta:
            try:
                parsed = json.loads(meta)
                if isinstance(parsed, dict):
                    meta_payload = parsed
            except Exception:
                raise HTTPException(status_code=422, detail="invalid_meta_json")

        doc_type_hint = str(meta_payload.get("doc_type") or session.document_type or "").strip() or "other"
        user_comment_raw = meta_payload.get("user_comment")
        user_comment = str(user_comment_raw).strip() if isinstance(user_comment_raw, str) else None

        await _save_public_document_upload(
            db,
            candidate,
            doc_type_hint,
            upload_file=file,
            storage_key=None,
            user_comment=user_comment,
        )
        session.attached_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)

        try:
            await send_candidate_documents_progress_telegram(
                db,
                tenant_id=str(tenant_id),
                candidate=candidate,
                source_doc_type=doc_type_hint,
            )
        except Exception:
            pass
        try:
            promoted = await sync_candidate_ready_for_handoff_gate(
                db,
                tenant_id=str(tenant_id),
                candidate=candidate,
                source="public_scan_upload",
            )
            if promoted:
                await db.commit()
        except Exception:
            pass

        return ScanSessionSchema(**serialize_scan_session(session))
