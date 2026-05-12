"""Candidate notes (tenant-scoped).

Non-internal notes respect recruitment handoff write lock (privileged override + audit).
Internal notes are intentionally isolated: a single INSERT with no recruitment/HR side effects
(see ``add_candidate_note`` docstring and ``test_candidate_internal_note_no_side_effects``).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.app.auth.deps import Role, get_current_user, require_roles, UserCtx
from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.db.session import async_session_maker
from backend.app.services.audit import log_audit_event
from backend.app.services.handoff import is_client_tenant
from backend.app.services.recruitment_handoff_write_guard import (
    RECRUITMENT_LOCK_OVERRIDE_ROLES,
    is_recruitment_recruiter_write_locked_by_handoff,
)

router = APIRouter(prefix="/api/v1/candidates", tags=["candidate-notes"])

ALLOW_NOTES_ROLES = (
    Role.supervisor,
    Role.administrator,
    Role.recruiter,
    Role.superadmin,
)


async def _get_db(request: Request) -> Any:
    dbi = getattr(getattr(request.app, "state", None), "db", None)
    if dbi is not None:
        return dbi
    raise HTTPException(status_code=500, detail="DB connection is not initialized")


def _to_iso(dt: Any) -> str:
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z") + (
            "" if str(dt.tzinfo or "").endswith("UTC") else ""
        )
    return str(dt)


def _map_note_row(row: Any) -> dict:
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    author_name = _get(row, "author_name") or _get(row, "author_email") or ""
    return {
        "id": str(_get(row, "id", "")),
        "text": _get(row, "text", ""),
        "visibility": _get(row, "visibility", "internal"),
        "author_id": str(_get(row, "author_id", "")),
        "author_name": str(author_name).strip() if author_name else None,
        "created_at": _to_iso(_get(row, "created_at")),
    }


class NoteIn(BaseModel):
    text: str = Field(min_length=1)
    visibility: str = Field(default="internal", pattern="^(internal|client|candidate)$")
    override_reason: Optional[str] = Field(
        default=None,
        description="Required with admin/supervisor/superadmin when recruitment is locked and visibility is not internal.",
    )


class NoteOut(BaseModel):
    id: str
    text: str
    visibility: str
    author_id: str
    author_name: str | None = None
    created_at: str


@router.get("/{candidate_id}/notes", response_model=List[NoteOut])
async def list_candidate_notes(
    candidate_id: str,
    request: Request,
    user: UserCtx = Depends(get_current_user),
    _=Depends(require_roles(*ALLOW_NOTES_ROLES)),
):
    dbi = await _get_db(request)
    rows = await dbi.fetch_all(
        """
        SELECT n.id, n.text, n.visibility, n.author_id, n.created_at,
               COALESCE(u.full_name, u.email, u.short_id::text, '') as author_name
        FROM candidate_notes n
        LEFT JOIN users u ON u.id = n.author_id
        WHERE n.candidate_id = :cid AND n.tenant_id = :tid
        ORDER BY n.created_at DESC
        """,
        {"cid": candidate_id, "tid": user.tenant_id},
    )
    return [_map_note_row(r) for r in rows]


@router.post("/{candidate_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def add_candidate_note(
    candidate_id: str,
    payload: NoteIn,
    request: Request,
    user: UserCtx = Depends(get_current_user),
    _=Depends(require_roles(*ALLOW_NOTES_ROLES)),
):
    """Append a tenant-scoped note row.

    **Internal visibility (``visibility=internal``):** no recruitment-handoff lock check and no
    follow-up writes (no candidate PATCH, no ``log_activity``/webhooks, no automation/SLA hooks).
    This endpoint is intentionally a single ``INSERT`` into ``candidate_notes`` so internal
    coordination cannot move stage/status or notify HR/client channels.

    **Non-internal:** subject to ``is_recruitment_recruiter_write_locked_by_handoff``; privileged
    bypass requires ``override_reason`` and emits ``recruitment_lock_write_override`` audit after success.
    """
    tenant_id = str(user.tenant_id)
    lock_override_note_ctx: Optional[dict[str, str]] = None
    if payload.visibility != "internal":
        async with async_session_maker() as check_db:
            try:
                await check_db.execute(
                    text("SELECT set_config('app.tenant_id', :tid, false)"),
                    {"tid": tenant_id},
                )
            except Exception:
                pass
            client = await is_client_tenant(check_db, tenant_id)
            if not client:
                locked, lock_reason = await is_recruitment_recruiter_write_locked_by_handoff(
                    check_db,
                    agency_tenant_id=tenant_id,
                    candidate_id=candidate_id,
                )
                if locked:
                    role_l = str(getattr(user, "role", "") or "").strip().lower()
                    or_ok = str(payload.override_reason or "").strip()
                    if role_l not in RECRUITMENT_LOCK_OVERRIDE_ROLES or not or_ok:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=(
                                f"Recruitment locked ({lock_reason or 'handoff'}): "
                                "cannot add client/candidate-visible note"
                            ),
                        )
                    lock_override_note_ctx = {
                        "lock_reason": lock_reason or "handoff",
                        "override_reason": or_ok,
                    }

    dbi = await _get_db(request)
    note_id = str(uuid.uuid4())

    author_id = str(user.sub or "").strip()
    if not author_id:
        raise HTTPException(status_code=500, detail="candidate_notes.add failed: user id is missing in context")

    await dbi.execute(
        """
        INSERT INTO candidate_notes (id, tenant_id, candidate_id, author_id, text, visibility)
        VALUES (:id, :tid, :cid, :uid, :text, :vis)
        """,
        {
            "id": note_id,
            "tid": tenant_id,
            "cid": candidate_id,
            "uid": author_id,
            "text": payload.text,
            "vis": payload.visibility,
        },
    )
    row = await dbi.fetch_one(
        """
        SELECT n.id, n.text, n.visibility, n.author_id, n.created_at,
               COALESCE(u.full_name, u.email, u.short_id::text, '') as author_name
        FROM candidate_notes n
        LEFT JOIN users u ON u.id = n.author_id
        WHERE n.id = :id AND n.tenant_id = :tid
        """,
        {"id": note_id, "tid": tenant_id},
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create note")
    if lock_override_note_ctx:
        async with async_session_maker() as adb:
            try:
                await log_audit_event(
                    adb,
                    tenant_id=tenant_id,
                    event_type=AuditEventType.recruitment_lock_write_override,
                    entity_type=AuditEntityType.candidate,
                    entity_id=candidate_id,
                    actor_id=author_id,
                    payload={
                        "operation": "candidate_process_note",
                        "lock_reason": lock_override_note_ctx["lock_reason"],
                        "override_reason": lock_override_note_ctx["override_reason"],
                        "actor_role": str(getattr(user, "role", "") or "").strip().lower(),
                        "note_visibility": payload.visibility,
                        "note_id": note_id,
                    },
                )
                await adb.commit()
            except Exception:
                await adb.rollback()
    return _map_note_row(row)
