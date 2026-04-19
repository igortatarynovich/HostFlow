from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
# В твоём проекте get_db живёт здесь:
from backend.app.db.deps import get_db, get_db_with_tenant
from backend.app.schemas.user import (
    NotificationsPreference,
    UserPasswordChange,
    UserSessionOut,
    UserAvatarOut,
    UserMeOut,
    UserMePatch,
)
from backend.app.services import users as users_service
from backend.app.services.users import UserServiceError

# backend/app/api/v1/users.py


router = APIRouter(prefix="/api/v1/users", tags=["users"])

DEV_TENANT_ID = "11111111-1111-1111-1111-111111111111"
UPLOAD_ROOT = Path(os.environ.get("UPLOAD_DIR") or Path(__file__).resolve().parents[2] / "uploads")
AVATAR_ROOT = UPLOAD_ROOT / "avatars"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _tenant_id_from_headers(request: Request) -> str:
    # Если фронт ещё не шлёт заголовок — берём DEV-tenant
    return request.headers.get("X-Tenant-Id", DEV_TENANT_ID)


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for tenant")


@router.get("/managers")
async def list_managers(
    request: Request,
    db: AsyncSession = Depends(get_db),
    roles: str | None = Query(
        default=None,
        description="Comma-separated membership roles (default: owner, administrator, supervisor, recruiter).",
    ),
):
    """
    Семантически правильный эндпоинт пользователей-менеджеров.
    Возвращает список словарей: {id, short_id, full_name, email, label}
    """
    tenant_id = _tenant_id_from_headers(request)
    role_list = (
        [p.strip() for p in roles.split(",") if p.strip()] if roles and roles.strip() else None
    )
    return await users_service.get_tenant_managers(
        db, tenant_id, membership_roles=role_list
    )


@router.get("/me", response_model=UserMeOut)
async def get_me(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        return await users_service.get_user_me(
            db,
            tenant_id=tenant_id,
            user_id=ctx.sub,
        )
    except UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch("/me", response_model=UserMeOut)
async def patch_me(
    payload: UserMePatch,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        profile_payload = payload.profile.model_dump(exclude_unset=True) if payload.profile else None
        preferences_payload = payload.preferences.model_dump(exclude_unset=True) if payload.preferences else None
        updated = await users_service.patch_user_me(
            db,
            tenant_id=tenant_id,
            user_id=ctx.sub,
            profile_payload=profile_payload,
            preferences_payload=preferences_payload,
        )
        await db.commit()
        return updated
    except UserServiceError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_self_password(
    payload: UserPasswordChange,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        await users_service.change_self_password(
            db,
            tenant_id=tenant_id,
            user_id=ctx.sub,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except UserServiceError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/me/avatar", response_model=UserAvatarOut)
async def upload_avatar(
    file: UploadFile = File(...),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)

    if file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    ext = ".png"
    if file.content_type == "image/jpeg":
        ext = ".jpg"
    elif file.content_type == "image/webp":
        ext = ".webp"

    tenant_dir = AVATAR_ROOT / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{ctx.sub}{ext}"
    path = tenant_dir / filename

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    with open(path, "wb") as buffer:
        buffer.write(data)

    public_url = f"/uploads/avatars/{tenant_id}/{filename}"

    try:
        result = await users_service.update_user_avatar(
            db,
            tenant_id=tenant_id,
            user_id=ctx.sub,
            avatar_url=public_url,
        )
        await db.commit()
        return result
    except UserServiceError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/me/notifications", response_model=Dict[str, NotificationsPreference])
async def get_notification_preferences(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        data = await users_service.get_notification_preferences(
            db,
            tenant_id=tenant_id,
            user_id=ctx.sub,
        )
        return data
    except UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch("/me/notifications", response_model=Dict[str, NotificationsPreference])
async def update_notification_preferences(
    payload: Dict[str, NotificationsPreference],
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        updates = {key: value.model_dump() for key, value in payload.items()}
        data = await users_service.update_notification_preferences(
            db,
            tenant_id=tenant_id,
            user_id=ctx.sub,
            updates=updates,
        )
        await db.commit()
        return data
    except UserServiceError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/me/sessions", response_model=List[UserSessionOut])
async def list_sessions(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        return await users_service.list_user_sessions(
            db,
            tenant_id=tenant_id,
            user_id=ctx.sub,
        )
    except UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.delete("/me/sessions", response_model=dict)
async def revoke_sessions(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        revoked = await users_service.revoke_user_sessions(
            db,
            tenant_id=tenant_id,
            user_id=ctx.sub,
        )
        await db.commit()
        return {"revoked": revoked}
    except UserServiceError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
