from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.schemas.user import (
    RefreshRevokeOut,
    UserCreate,
    UserCreateInvite,
    UserDetailOut,
    UserInviteOut,
    UserOut,
    AdminPasswordChange,
    UserPasswordResetOut,
    UserDeleteOut,
    UserRole,
    UserSupervisorUpdate,
    UserCompaniesUpdate,
    UserUpdateRole,
    UserAuditOut,
)
from backend.app.services import users as users_service
from backend.app.services.users import UserServiceError

router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
    redirect_slashes=False,
)


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    if (ctx.role or "").strip().lower() == Role.superadmin.value:
        return
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden for tenant")


def _handle_service_error(exc: UserServiceError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "",
    response_model=list[UserOut],
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def list_users(
    role: Optional[UserRole] = Query(default=None),
    supervisor_id: Optional[str] = Query(default=None),
    company_id: Optional[str] = Query(default=None),
    active: Optional[bool] = Query(default=None),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    items = await users_service.list_users(
        db,
        tenant_id,
        role=role.value if role else None,
        supervisor_id=supervisor_id,
        company_id=company_id,
        active=active,
    )
    return [UserOut(**item) for item in items]


@router.get(
    "/{user_id}",
    response_model=UserDetailOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def get_user(
    user_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        detail = await users_service.get_user_detail(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
        )
    except UserServiceError as exc:
        _handle_service_error(exc)
    return UserDetailOut(**detail)


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def create_user(
    payload: UserCreate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        entry, tmp_password = await users_service.create_user(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            email=payload.email,
            role=payload.role.value,
            full_name=payload.full_name,
            short_id=payload.short_id,
            password=payload.password,
            supervisor_id=payload.supervisor_id,
            company_ids=payload.company_ids,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    if tmp_password:
        entry["temporary_password"] = tmp_password
    return UserOut(**entry)


@router.post(
    "/invite",
    response_model=UserInviteOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def create_invite(
    payload: UserCreateInvite,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        invite, token = await users_service.create_invite(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            email=payload.email,
            role=payload.role.value,
            supervisor_id=payload.supervisor_id,
            company_ids=payload.company_ids,
            expires_in_hours=payload.expires_in_hours,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    return UserInviteOut(
        id=invite.id,
        email=invite.email,
        role=UserRole(invite.role),
        token=token,
        expires_at=invite.expires_at,
        status="pending",
        invited_user_id=invite.invited_user_id,
        supervisor_id=invite.supervisor_id,
        company_ids=list(invite.companies or []),
    )


@router.patch(
    "/{user_id}/role",
    response_model=UserOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def update_role(
    user_id: str,
    payload: UserUpdateRole,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        entry = await users_service.change_user_role(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            user_id=user_id,
            role=payload.role.value,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    return UserOut(**entry)


@router.patch(
    "/{user_id}/supervisor",
    response_model=UserOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def update_supervisor(
    user_id: str,
    payload: UserSupervisorUpdate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        entry = await users_service.update_user_supervisor(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            user_id=user_id,
            supervisor_id=payload.supervisor_id,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    return UserOut(**entry)


@router.patch(
    "/{user_id}/companies",
    response_model=UserDetailOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def update_user_companies(
    user_id: str,
    payload: UserCompaniesUpdate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        detail = await users_service.update_user_companies(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            user_id=user_id,
            company_ids=payload.company_ids,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    return UserDetailOut(**detail)


@router.post(
    "/{user_id}/sessions/revoke",
    response_model=RefreshRevokeOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def revoke_sessions(
    user_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        revoked = await users_service.revoke_user_refresh_tokens(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            user_id=user_id,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    return RefreshRevokeOut(revoked=revoked)


@router.post(
    "/{user_id}/revoke-refresh",
    response_model=RefreshRevokeOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def revoke_refresh_legacy(
    user_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    return await revoke_sessions(user_id, ctx, db_tenant)


@router.post(
    "/{user_id}/password/reset",
    response_model=UserPasswordResetOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def reset_password(
    user_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        new_password, revoked = await users_service.reset_user_password(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            user_id=user_id,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    return UserPasswordResetOut(temporary_password=new_password, revoked_sessions=revoked)


@router.post(
    "/{user_id}/password",
    response_model=RefreshRevokeOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def change_password(
    user_id: str,
    payload: AdminPasswordChange,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        revoked = await users_service.change_user_password(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            user_id=user_id,
            new_password=payload.new_password,
            revoke_sessions=payload.revoke_sessions,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    return RefreshRevokeOut(revoked=revoked)


@router.post(
    "/{user_id}/activate",
    response_model=UserOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def activate_user(
    user_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        entry = await users_service.set_user_active(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            user_id=user_id,
            is_active=True,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    return UserOut(**entry)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def deactivate_user(
    user_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    if ctx.sub == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate self")
    try:
        entry = await users_service.set_user_active(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            user_id=user_id,
            is_active=False,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    return UserOut(**entry)


@router.delete(
    "/{user_id}",
    response_model=UserDeleteOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def delete_user(
    user_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        result = await users_service.delete_user(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            user_id=user_id,
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        _handle_service_error(exc)
    return UserDeleteOut(deleted=True, revoked_sessions=result.get("revoked_sessions", 0))


@router.get(
    "/{user_id}/audit",
    response_model=list[UserAuditOut],
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def user_audit(
    user_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    logs = await users_service.list_user_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        limit=limit,
    )
    return [
        UserAuditOut(
            id=log.id,
            tenant_id=log.tenant_id,
            user_id=log.user_id,
            actor_id=log.actor_id,
            action=log.action,
            payload=log.payload,
            created_at=log.created_at,
        )
        for log in logs
    ]
