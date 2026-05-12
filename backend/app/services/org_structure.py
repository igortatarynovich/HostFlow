"""Org units (departments / teams) and memberships — tenant scoped."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Set

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.org_unit import OrgUnit, OrgUnitMember
from backend.app.models.user import User
from backend.app.schemas.org_structure import OrgUnitImportRow


class OrgStructureError(Exception):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def assert_org_unit_exists(db: AsyncSession, tenant_id: str, unit_id: str | None) -> None:
    if not unit_id:
        return
    if not await _get_unit(db, tenant_id, unit_id):
        raise OrgStructureError("Org unit not found", 404)


async def _get_unit(db: AsyncSession, tenant_id: str, unit_id: str) -> OrgUnit | None:
    stmt = select(OrgUnit).where(OrgUnit.tenant_id == tenant_id).where(OrgUnit.id == unit_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_org_unit(db: AsyncSession, tenant_id: str, unit_id: str) -> OrgUnit | None:
    """Return a single org unit row (for API/audit); prefer over internal _get_unit from other packages."""
    return await _get_unit(db, tenant_id, unit_id)


async def _parent_chain_ids(db: AsyncSession, tenant_id: str, unit_id: str) -> List[str]:
    out: List[str] = []
    cur: str | None = unit_id
    seen: Set[str] = set()
    while cur:
        if cur in seen:
            break
        seen.add(cur)
        row = await _get_unit(db, tenant_id, cur)
        if not row:
            break
        out.append(row.id)
        cur = row.parent_id
    return out


async def assert_parent_not_descendant(
    db: AsyncSession,
    *,
    tenant_id: str,
    unit_id: str,
    new_parent_id: str | None,
) -> None:
    if not new_parent_id:
        return
    if new_parent_id == unit_id:
        raise OrgStructureError("Org unit cannot be its own parent", 422)
    chain = await _parent_chain_ids(db, tenant_id, new_parent_id)
    if unit_id in chain:
        raise OrgStructureError("Parent would create a cycle in org unit tree", 422)


async def list_units_flat(db: AsyncSession, tenant_id: str) -> List[OrgUnit]:
    stmt = select(OrgUnit).where(OrgUnit.tenant_id == tenant_id).order_by(OrgUnit.sort_order, OrgUnit.name)
    return list((await db.execute(stmt)).scalars().all())


def build_tree_rows(rows: Sequence[OrgUnit]) -> List[Dict[str, Any]]:
    by_parent: Dict[str | None, List[OrgUnit]] = {}
    for r in rows:
        by_parent.setdefault(r.parent_id, []).append(r)
    for lst in by_parent.values():
        lst.sort(key=lambda x: (x.sort_order, x.name or ""))

    def walk(parent_id: str | None) -> List[Dict[str, Any]]:
        nodes: List[Dict[str, Any]] = []
        for u in by_parent.get(parent_id, []):
            nodes.append(
                {
                    "id": u.id,
                    "tenant_id": u.tenant_id,
                    "parent_id": u.parent_id,
                    "name": u.name,
                    "unit_type": u.unit_type,
                    "code": u.code,
                    "leader_user_id": u.leader_user_id,
                    "sort_order": u.sort_order,
                    "meta": u.meta or {},
                    "children": walk(u.id),
                }
            )
        return nodes

    return walk(None)


async def get_tree(db: AsyncSession, tenant_id: str) -> List[Dict[str, Any]]:
    rows = await list_units_flat(db, tenant_id)
    return build_tree_rows(rows)


async def create_unit(
    db: AsyncSession,
    *,
    tenant_id: str,
    name: str,
    parent_id: str | None = None,
    unit_type: str = "department",
    code: str | None = None,
    leader_user_id: str | None = None,
    sort_order: int = 0,
    meta: dict[str, Any] | None = None,
) -> OrgUnit:
    name = (name or "").strip()
    if not name:
        raise OrgStructureError("Name is required", 422)
    if parent_id:
        p = await _get_unit(db, tenant_id, parent_id)
        if not p:
            raise OrgStructureError("Parent org unit not found", 404)
    row = OrgUnit(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        parent_id=parent_id,
        name=name,
        unit_type=(unit_type or "department").strip()[:32] or "department",
        code=(code or "").strip()[:64] or None,
        leader_user_id=leader_user_id,
        sort_order=int(sort_order),
        meta=meta or {},
    )
    db.add(row)
    await db.flush()
    return row


async def patch_unit(
    db: AsyncSession,
    *,
    tenant_id: str,
    unit_id: str,
    **fields: Any,
) -> OrgUnit:
    row = await _get_unit(db, tenant_id, unit_id)
    if not row:
        raise OrgStructureError("Org unit not found", 404)

    allowed = {"name", "parent_id", "unit_type", "code", "leader_user_id", "sort_order", "meta"}
    for k in fields:
        if k not in allowed:
            raise OrgStructureError(f"Unsupported field: {k}", 422)

    if "parent_id" in fields:
        parent_id = fields["parent_id"]
        if parent_id == unit_id:
            raise OrgStructureError("Org unit cannot be its own parent", 422)
        if parent_id:
            p = await _get_unit(db, tenant_id, parent_id)
            if not p:
                raise OrgStructureError("Parent org unit not found", 404)
            await assert_parent_not_descendant(db, tenant_id=tenant_id, unit_id=unit_id, new_parent_id=parent_id)
        row.parent_id = parent_id

    if "name" in fields and fields["name"] is not None:
        n = str(fields["name"]).strip()
        if not n:
            raise OrgStructureError("Name is required", 422)
        row.name = n
    if "unit_type" in fields and fields["unit_type"] is not None:
        row.unit_type = (str(fields["unit_type"]) or "department").strip()[:32] or "department"
    if "code" in fields:
        c = fields["code"]
        row.code = (str(c).strip()[:64] or None) if c is not None else None
    if "leader_user_id" in fields:
        row.leader_user_id = fields["leader_user_id"] or None
    if "sort_order" in fields and fields["sort_order"] is not None:
        row.sort_order = int(fields["sort_order"])
    if "meta" in fields and fields["meta"] is not None:
        row.meta = fields["meta"]
    row.updated_at = _now()
    await db.flush()
    return row


async def delete_unit(db: AsyncSession, *, tenant_id: str, unit_id: str) -> None:
    row = await _get_unit(db, tenant_id, unit_id)
    if not row:
        raise OrgStructureError("Org unit not found", 404)
    child = (
        await db.execute(select(func.count()).select_from(OrgUnit).where(OrgUnit.parent_id == unit_id))
    ).scalar_one()
    if int(child or 0) > 0:
        raise OrgStructureError("Remove or reassign child org units first", 409)
    await db.execute(sa.delete(OrgUnitMember).where(OrgUnitMember.org_unit_id == unit_id))
    await db.execute(sa.delete(OrgUnit).where(OrgUnit.id == unit_id).where(OrgUnit.tenant_id == tenant_id))
    await db.flush()


async def list_members(db: AsyncSession, *, tenant_id: str, unit_id: str) -> List[Dict[str, Any]]:
    u = await _get_unit(db, tenant_id, unit_id)
    if not u:
        raise OrgStructureError("Org unit not found", 404)
    from backend.app.models.user import User

    stmt = (
        select(OrgUnitMember, User.email, User.full_name, User.short_id)
        .join(User, User.id == OrgUnitMember.user_id)
        .where(OrgUnitMember.tenant_id == tenant_id)
        .where(OrgUnitMember.org_unit_id == unit_id)
    )
    rows = (await db.execute(stmt)).all()
    out: List[Dict[str, Any]] = []
    for m, email, full_name, short_id in rows:
        out.append(
            {
                "user_id": m.user_id,
                "role_in_unit": m.role_in_unit,
                "email": email,
                "full_name": full_name,
                "short_id": short_id,
            }
        )
    return out


async def add_member(
    db: AsyncSession,
    *,
    tenant_id: str,
    unit_id: str,
    user_id: str,
    role_in_unit: str = "member",
) -> OrgUnitMember:
    u = await _get_unit(db, tenant_id, unit_id)
    if not u:
        raise OrgStructureError("Org unit not found", 404)
    existing = (
        await db.execute(
            select(OrgUnitMember)
            .where(OrgUnitMember.tenant_id == tenant_id)
            .where(OrgUnitMember.org_unit_id == unit_id)
            .where(OrgUnitMember.user_id == user_id)
        )
    ).scalar_one_or_none()
    if existing:
        existing.role_in_unit = (role_in_unit or "member").strip()[:32] or "member"
        existing.updated_at = _now()
        await db.flush()
        return existing
    m = OrgUnitMember(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        org_unit_id=unit_id,
        user_id=user_id,
        role_in_unit=(role_in_unit or "member").strip()[:32] or "member",
    )
    db.add(m)
    await db.flush()
    return m


async def remove_member(db: AsyncSession, *, tenant_id: str, unit_id: str, user_id: str) -> None:
    stmt = (
        sa.delete(OrgUnitMember)
        .where(OrgUnitMember.tenant_id == tenant_id)
        .where(OrgUnitMember.org_unit_id == unit_id)
        .where(OrgUnitMember.user_id == user_id)
    )
    await db.execute(stmt)
    await db.flush()


async def list_user_org_units(db: AsyncSession, *, tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
    stmt = (
        select(OrgUnitMember, OrgUnit.name)
        .join(OrgUnit, OrgUnit.id == OrgUnitMember.org_unit_id)
        .where(OrgUnitMember.tenant_id == tenant_id)
        .where(OrgUnitMember.user_id == user_id)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {"org_unit_id": m.org_unit_id, "name": name, "role_in_unit": m.role_in_unit}
        for m, name in rows
    ]


async def set_user_org_units(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    org_unit_ids: Sequence[str],
) -> None:
    """Replace memberships with role `member` for the given unit ids."""
    ids = [str(x).strip() for x in org_unit_ids if str(x).strip()]
    for uid in ids:
        u = await _get_unit(db, tenant_id, uid)
        if not u:
            raise OrgStructureError(f"Org unit not found: {uid}", 404)

    await db.execute(
        sa.delete(OrgUnitMember).where(OrgUnitMember.tenant_id == tenant_id).where(OrgUnitMember.user_id == user_id)
    )
    for uid in ids:
        db.add(
            OrgUnitMember(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                org_unit_id=uid,
                user_id=user_id,
                role_in_unit="member",
            )
        )
    await db.flush()


async def _leader_allowed(db: AsyncSession, tenant_id: str, leader_user_id: str | None) -> str | None:
    if not leader_user_id:
        return None
    stmt = (
        select(User.id)
        .where(User.id == leader_user_id)
        .where(User.tenant_id == tenant_id)
        .where(User.deleted_at.is_(None))
    )
    ok = (await db.execute(stmt)).scalar_one_or_none()
    return leader_user_id if ok else None


def order_import_rows_for_merge(rows: Sequence[OrgUnitImportRow], *, db_codes: Set[str]) -> List[OrgUnitImportRow]:
    """Topological order for rows in the import file. Parents may be satisfied by existing tenant codes (`db_codes`)."""
    stripped_rows: List[OrgUnitImportRow] = []
    for r in rows:
        stripped_rows.append(
            OrgUnitImportRow(
                code=(r.code or "").strip(),
                name=r.name,
                parent_code=(r.parent_code or "").strip() or None,
                unit_type=r.unit_type,
                sort_order=r.sort_order,
                leader_user_id=r.leader_user_id,
                meta=r.meta,
            )
        )
    rows_list = stripped_rows
    by_code = {r.code: r for r in rows_list}
    codes = list(by_code.keys())
    if len(by_code) != len(rows_list):
        raise OrgStructureError("Duplicate code in import payload", 422)
    indegree: Dict[str, int] = {c: 0 for c in codes}
    children: Dict[str, List[str]] = {c: [] for c in codes}
    for r in rows_list:
        c = r.code
        pc = r.parent_code
        if pc:
            if pc not in by_code and pc not in db_codes:
                raise OrgStructureError(
                    f"parent_code not found in import file or tenant: {pc}",
                    422,
                )
            if pc in by_code:
                children[pc].append(c)
                indegree[c] += 1
    queue = [c for c in codes if indegree[c] == 0]
    ordered_codes: List[str] = []
    while queue:
        c = queue.pop(0)
        ordered_codes.append(c)
        for ch in children[c]:
            indegree[ch] -= 1
            if indegree[ch] == 0:
                queue.append(ch)
    if len(ordered_codes) != len(codes):
        raise OrgStructureError("Import rows contain a cycle or inconsistent parents", 422)
    return [by_code[c] for c in ordered_codes]


async def export_org_structure_snapshot(db: AsyncSession, tenant_id: str) -> Dict[str, Any]:
    rows = await list_units_flat(db, tenant_id)
    by_id = {r.id: r for r in rows}
    units: List[Dict[str, Any]] = []
    for r in rows:
        parent_code: str | None = None
        if r.parent_id and r.parent_id in by_id:
            p = by_id[r.parent_id]
            parent_code = (p.code or "").strip() or None
        units.append(
            {
                "id": r.id,
                "parent_id": r.parent_id,
                "parent_code": parent_code,
                "code": r.code,
                "name": r.name,
                "unit_type": r.unit_type,
                "sort_order": r.sort_order,
                "leader_user_id": r.leader_user_id,
                "meta": r.meta or {},
            }
        )
    return {"version": 1, "tenant_id": tenant_id, "units": units}


async def import_org_units_merge_by_code(
    db: AsyncSession,
    *,
    tenant_id: str,
    rows: Sequence[OrgUnitImportRow],
) -> Dict[str, int]:
    """Create or update units keyed by `code`. Parents resolve via `parent_code` (existing tenant units or rows in this batch)."""
    if not rows:
        return {"created": 0, "updated": 0}

    existing_flat = await list_units_flat(db, tenant_id)
    db_codes: Set[str] = {str(u.code).strip() for u in existing_flat if u.code and str(u.code).strip()}
    code_to_id: Dict[str, str] = {}
    for u in existing_flat:
        if u.code and str(u.code).strip():
            code_to_id[str(u.code).strip()] = u.id

    ordered = order_import_rows_for_merge(list(rows), db_codes=db_codes)

    created = 0
    updated = 0

    for r in ordered:
        code = r.code
        pc = r.parent_code
        parent_id: str | None = None
        if pc:
            parent_id = code_to_id.get(pc)
            if not parent_id:
                raise OrgStructureError(
                    f"parent_code not found in tenant or earlier import rows: {pc}",
                    422,
                )

        leader_id = await _leader_allowed(db, tenant_id, r.leader_user_id)

        uid = code_to_id.get(code)
        meta = r.meta if r.meta is not None else {}

        if uid:
            await patch_unit(
                db,
                tenant_id=tenant_id,
                unit_id=uid,
                name=r.name,
                parent_id=parent_id,
                unit_type=r.unit_type,
                sort_order=r.sort_order,
                leader_user_id=leader_id,
                meta=meta,
            )
            updated += 1
        else:
            row = await create_unit(
                db,
                tenant_id=tenant_id,
                name=r.name,
                parent_id=parent_id,
                unit_type=r.unit_type,
                code=code,
                leader_user_id=leader_id,
                sort_order=r.sort_order,
                meta=meta,
            )
            code_to_id[code] = row.id
            created += 1

    await db.flush()
    return {"created": created, "updated": updated}
