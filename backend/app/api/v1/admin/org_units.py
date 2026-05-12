from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.schemas.org_structure import (
    OrgUnitCreate,
    OrgUnitMemberAdd,
    OrgUnitPatch,
    OrgStructureImport,
)
from backend.app.services.audit import log_activity
from backend.app.services import org_structure as org_svc
from backend.app.services.org_structure import OrgStructureError
from backend.app.services.users import record_user_audit

router = APIRouter(prefix="/admin/org-units", tags=["admin-org-units"])

# Tenant administrators and supervisors may maintain org tree and unit membership.
_ORG_UNIT_MANAGER_ROLES = (Role.administrator, Role.supervisor)


def _handle(exc: OrgStructureError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/tree", response_model=List[Dict[str, Any]], dependencies=[Depends(require_roles(*_ORG_UNIT_MANAGER_ROLES))])
async def org_tree(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tid = db_tenant
    tenant_id = str(tid)
    return await org_svc.get_tree(db, tenant_id)


@router.get("/export", response_model=Dict[str, Any], dependencies=[Depends(require_roles(*_ORG_UNIT_MANAGER_ROLES))])
async def org_export(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tid = db_tenant
    tenant_id = str(tid)
    return await org_svc.export_org_structure_snapshot(db, tenant_id)


@router.post("/import", response_model=Dict[str, Any], dependencies=[Depends(require_roles(*_ORG_UNIT_MANAGER_ROLES))])
async def org_import(
    payload: OrgStructureImport,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tid = db_tenant
    tenant_id = str(tid)
    try:
        summary = await org_svc.import_org_units_merge_by_code(db, tenant_id=tenant_id, rows=payload.units)
        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            target_user_id=None,
            action="org_unit.import",
            payload=dict(summary),
        )
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            action="org_unit.import",
            target_type="org_unit",
            target_id=None,
            payload=dict(summary),
        )
        await db.commit()
    except OrgStructureError as exc:
        await db.rollback()
        _handle(exc)
    return summary


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def org_create(
    payload: OrgUnitCreate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
    _: str = Depends(require_roles(*_ORG_UNIT_MANAGER_ROLES)),
):
    db, tid = db_tenant
    tenant_id = str(tid)
    try:
        row = await org_svc.create_unit(
            db,
            tenant_id=tenant_id,
            name=payload.name,
            parent_id=payload.parent_id,
            unit_type=payload.unit_type,
            code=payload.code,
            leader_user_id=payload.leader_user_id,
            sort_order=payload.sort_order,
            meta=payload.meta,
        )
        pl = {
            "name": row.name,
            "parent_id": row.parent_id,
            "unit_type": row.unit_type,
            "code": row.code,
            "leader_user_id": row.leader_user_id,
            "sort_order": row.sort_order,
        }
        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            target_user_id=None,
            action="org_unit.created",
            payload=pl,
        )
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            action="org_unit.created",
            target_type="org_unit",
            target_id=row.id,
            payload=pl,
        )
        await db.commit()
    except OrgStructureError as exc:
        await db.rollback()
        _handle(exc)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "parent_id": row.parent_id,
        "name": row.name,
        "unit_type": row.unit_type,
        "code": row.code,
        "leader_user_id": row.leader_user_id,
        "sort_order": row.sort_order,
        "meta": row.meta or {},
    }


@router.patch("/{unit_id}", response_model=Dict[str, Any], dependencies=[Depends(require_roles(*_ORG_UNIT_MANAGER_ROLES))])
async def org_patch(
    unit_id: str,
    payload: OrgUnitPatch,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tid = db_tenant
    tenant_id = str(tid)
    try:
        updates = payload.model_dump(exclude_unset=True)
        row = await org_svc.patch_unit(db, tenant_id=tenant_id, unit_id=unit_id, **updates)
        pl = {"org_unit_id": unit_id, "changes": updates}
        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            target_user_id=None,
            action="org_unit.updated",
            payload=pl,
        )
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            action="org_unit.updated",
            target_type="org_unit",
            target_id=unit_id,
            payload=pl,
        )
        await db.commit()
    except OrgStructureError as exc:
        await db.rollback()
        _handle(exc)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "parent_id": row.parent_id,
        "name": row.name,
        "unit_type": row.unit_type,
        "code": row.code,
        "leader_user_id": row.leader_user_id,
        "sort_order": row.sort_order,
        "meta": row.meta or {},
    }


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def org_delete(
    unit_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
    _: str = Depends(require_roles(*_ORG_UNIT_MANAGER_ROLES)),
):
    db, tid = db_tenant
    tenant_id = str(tid)
    try:
        before = await org_svc.get_org_unit(db, tenant_id, unit_id)
        if not before:
            raise OrgStructureError("Org unit not found", 404)
        snap = {
            "name": before.name,
            "parent_id": before.parent_id,
            "unit_type": before.unit_type,
            "code": before.code,
        }
        await org_svc.delete_unit(db, tenant_id=tenant_id, unit_id=unit_id)
        pl = {"org_unit_id": unit_id, **snap}
        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            target_user_id=None,
            action="org_unit.deleted",
            payload=pl,
        )
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            action="org_unit.deleted",
            target_type="org_unit",
            target_id=unit_id,
            payload=pl,
        )
        await db.commit()
    except OrgStructureError as exc:
        await db.rollback()
        _handle(exc)


@router.get("/{unit_id}/members", response_model=List[Dict[str, Any]])
async def org_members_list(
    unit_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
    _: str = Depends(require_roles(*_ORG_UNIT_MANAGER_ROLES)),
):
    db, tid = db_tenant
    tenant_id = str(tid)
    try:
        return await org_svc.list_members(db, tenant_id=tenant_id, unit_id=unit_id)
    except OrgStructureError as exc:
        _handle(exc)


@router.post("/{unit_id}/members", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def org_members_add(
    unit_id: str,
    payload: OrgUnitMemberAdd,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
    _: str = Depends(require_roles(*_ORG_UNIT_MANAGER_ROLES)),
):
    db, tid = db_tenant
    tenant_id = str(tid)
    try:
        m = await org_svc.add_member(
            db,
            tenant_id=tenant_id,
            unit_id=unit_id,
            user_id=payload.user_id,
            role_in_unit=payload.role_in_unit,
        )
        pl = {"org_unit_id": unit_id, "role_in_unit": m.role_in_unit}
        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            target_user_id=payload.user_id,
            action="org_unit.member_added",
            payload=pl,
        )
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            action="org_unit.member_added",
            target_type="org_unit",
            target_id=unit_id,
            payload={**pl, "user_id": payload.user_id},
        )
        await db.commit()
    except OrgStructureError as exc:
        await db.rollback()
        _handle(exc)
    return {"user_id": m.user_id, "role_in_unit": m.role_in_unit, "org_unit_id": m.org_unit_id}


@router.delete("/{unit_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def org_members_remove(
    unit_id: str,
    user_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
    _: str = Depends(require_roles(*_ORG_UNIT_MANAGER_ROLES)),
):
    db, tid = db_tenant
    tenant_id = str(tid)
    try:
        await org_svc.remove_member(db, tenant_id=tenant_id, unit_id=unit_id, user_id=user_id)
        pl = {"org_unit_id": unit_id}
        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            target_user_id=user_id,
            action="org_unit.member_removed",
            payload=pl,
        )
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=ctx.sub,
            action="org_unit.member_removed",
            target_type="org_unit",
            target_id=unit_id,
            payload={**pl, "user_id": user_id},
        )
        await db.commit()
    except OrgStructureError as exc:
        await db.rollback()
        _handle(exc)
