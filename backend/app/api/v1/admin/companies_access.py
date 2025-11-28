from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.schemas.access import CompanyAccessEntry, CompanyAccessGrant
from backend.app.services import access as access_service
from backend.app.services.audit import log_activity
from backend.app.services.users import UserServiceError, _load_user, record_user_audit

router = APIRouter(
    prefix="/admin/companies",
    tags=["admin-companies-access"],
    redirect_slashes=False,
)


def _require_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")


def _role_value(role: object) -> str:
    if hasattr(role, "value"):
        return str(getattr(role, "value"))
    return str(role or "")


def _enforce_supervisor_scope(ctx: UserCtx, user) -> None:
    if ctx.role == Role.supervisor.value:
        value = _role_value(user.role).lower()
        if value in {Role.administrator.value, Role.supervisor.value}:
            raise HTTPException(status_code=403, detail="Supervisor cannot manage this role")
        if user.id != ctx.sub and (user.supervisor_id or "") != ctx.sub:
            raise HTTPException(
                status_code=403,
                detail="Supervisor can manage access only for own recruiters",
            )


def _filter_entries_for_actor(ctx: UserCtx, rows):
    if ctx.role != Role.supervisor.value:
        return rows
    filtered = []
    for access, user in rows:
        if user.id == ctx.sub or (user.supervisor_id or "") == ctx.sub:
            filtered.append((access, user))
    return filtered


@router.get(
    "/{company_id}/access",
    response_model=list[CompanyAccessEntry],
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def get_access(
    company_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _require_tenant(ctx, tenant_id)
    rows = await access_service.list_company_access_with_users(
        db, tenant_id=tenant_id, company_id=company_id
    )
    entries: list[CompanyAccessEntry] = []
    for access, user in _filter_entries_for_actor(ctx, rows):
        entries.append(
            CompanyAccessEntry(
                user_id=user.id,
                email=user.email,
                role=_role_value(user.role),
                full_name=user.full_name,
                short_id=user.short_id,
                supervisor_id=user.supervisor_id,
                can_edit=bool(access.can_edit),
            )
        )
    return entries


@router.post(
    "/{company_id}/access",
    response_model=CompanyAccessEntry,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def grant_access(
    company_id: str,
    payload: CompanyAccessGrant,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _require_tenant(ctx, tenant_id)

    try:
        user = await _load_user(db, tenant_id=tenant_id, user_id=payload.user_id)
    except UserServiceError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    _enforce_supervisor_scope(ctx, user)

    if _role_value(user.role).lower() == Role.administrator.value:
        raise HTTPException(status_code=400, detail="Administrators have access by default")

    try:
        access = await access_service.grant_company_access(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            user_id=user.id,
            can_edit=payload.can_edit,
        )
        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            target_user_id=user.id,
            action="company.access_granted",
            payload={"company_id": company_id, "can_edit": bool(access.can_edit)},
        )
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            action="company.access_granted",
            target_type="company",
            target_id=company_id,
            payload={"user_id": user.id, "can_edit": bool(access.can_edit)},
        )
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise

    return CompanyAccessEntry(
        user_id=user.id,
        email=user.email,
        role=_role_value(user.role),
        full_name=user.full_name,
        short_id=user.short_id,
        supervisor_id=user.supervisor_id,
        can_edit=bool(access.can_edit),
    )


@router.delete(
    "/{company_id}/access/{user_id}",
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def revoke_access(
    company_id: str,
    user_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _require_tenant(ctx, tenant_id)

    try:
        user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    except UserServiceError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    _enforce_supervisor_scope(ctx, user)

    try:
        await access_service.revoke_company_access(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            user_id=user_id,
        )
        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            target_user_id=user.id,
            action="company.access_revoked",
            payload={"company_id": company_id},
        )
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            action="company.access_revoked",
            target_type="company",
            target_id=company_id,
            payload={"user_id": user.id},
        )
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise
    return {"ok": True}
