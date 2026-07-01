"""Admin org-units API: tree, CRUD, members, invite with org_unit_id."""

import uuid
from typing import Any, Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models.audit import UserAuditLog
from backend.tests.conftest import _init_data, _set_tenant

ORG_PREFIX = "/api/v1/admin/org-units"
USERS_PREFIX = "/api/v1/admin/users"


def _find_unit(tree: list[dict[str, Any]], unit_id: str) -> dict[str, Any] | None:
    for n in tree:
        if n.get("id") == unit_id:
            return n
        ch = n.get("children") or []
        if isinstance(ch, list):
            hit = _find_unit(ch, unit_id)
            if hit:
                return hit
    return None


@pytest.mark.anyio
async def test_org_structure_export_and_import_merge(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    h = {**manager_headers, "Content-Type": "application/json"}
    root_code = f"EXP-{uuid.uuid4().hex[:6]}"
    child_code = f"EXP-{uuid.uuid4().hex[:6]}"

    imp = await client.post(
        f"{ORG_PREFIX}/import",
        headers=h,
        json={
            "version": 1,
            "units": [
                {"code": root_code, "name": "Root import", "unit_type": "division", "sort_order": 0},
                {
                    "code": child_code,
                    "name": "Child import",
                    "parent_code": root_code,
                    "unit_type": "department",
                    "sort_order": 1,
                },
            ],
        },
    )
    assert imp.status_code == 200, imp.text
    assert imp.json().get("created") == 2
    assert imp.json().get("updated") == 0

    exp = await client.get(f"{ORG_PREFIX}/export", headers=h)
    assert exp.status_code == 200, exp.text
    body = exp.json()
    assert body.get("version") == 1
    units = body.get("units") or []
    codes = {u.get("code") for u in units}
    assert root_code in codes and child_code in codes

    upd = await client.post(
        f"{ORG_PREFIX}/import",
        headers=h,
        json={
            "version": 1,
            "units": [
                {"code": root_code, "name": "Root import renamed", "unit_type": "division", "sort_order": 0},
                {
                    "code": child_code,
                    "name": "Child import",
                    "parent_code": root_code,
                    "unit_type": "department",
                    "sort_order": 2,
                },
            ],
        },
    )
    assert upd.status_code == 200, upd.text
    assert upd.json().get("updated") == 2

    # cleanup (child first if nested — delete leaf without children)
    tree = await client.get(f"{ORG_PREFIX}/tree", headers=h)
    assert tree.status_code == 200

    def find_id(nodes: list, code: str) -> str | None:
        for n in nodes:
            if n.get("code") == code:
                return n.get("id")
            ch = n.get("children") or []
            if isinstance(ch, list):
                hit = find_id(ch, code)
                if hit:
                    return hit
        return None

    tid_child = find_id(tree.json(), child_code)
    tid_root = find_id(tree.json(), root_code)
    assert tid_child and tid_root
    await client.delete(f"{ORG_PREFIX}/{tid_child}", headers=h)
    await client.delete(f"{ORG_PREFIX}/{tid_root}", headers=h)


@pytest.mark.anyio
async def test_org_tree_supervisor_ok(client: AsyncClient, supervisor_headers: Dict[str, str]) -> None:
    resp = await client.get(f"{ORG_PREFIX}/tree", headers=supervisor_headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_org_unit_create_writes_user_audit_log(
    client: AsyncClient, manager_headers: Dict[str, str], tenant_id: str
) -> None:
    """org_unit.created should appear in user_audit_log for /admin/audit."""
    h = {**manager_headers, "Content-Type": "application/json"}
    name = f"Audit-{uuid.uuid4().hex[:8]}"
    create = await client.post(
        ORG_PREFIX,
        headers=h,
        json={"name": name, "unit_type": "department"},
    )
    assert create.status_code == 201, create.text
    unit_id = create.json()["id"]

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        result = await session.execute(
            select(UserAuditLog)
            .where(UserAuditLog.tenant_id == tenant_id)
            .where(UserAuditLog.action == "org_unit.created")
            .order_by(UserAuditLog.created_at.desc())
            .limit(10)
        )
        logs = list(result.scalars().all())
    assert any((log.payload or {}).get("name") == name for log in logs), logs

    await client.delete(f"{ORG_PREFIX}/{unit_id}", headers=h)


@pytest.mark.anyio
async def test_org_tree_viewer_forbidden(client: AsyncClient, viewer_headers: Dict[str, str]) -> None:
    resp = await client.get(f"{ORG_PREFIX}/tree", headers=viewer_headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.anyio
async def test_admin_users_list_supervisor_ok(client: AsyncClient, supervisor_headers: Dict[str, str]) -> None:
    resp = await client.get(USERS_PREFIX, headers=supervisor_headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_org_tree_list_and_crud_flow(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    h = {**manager_headers, "Content-Type": "application/json"}
    tree0 = await client.get(f"{ORG_PREFIX}/tree", headers=h)
    assert tree0.status_code == 200, tree0.text
    assert isinstance(tree0.json(), list)

    name = f"Unit-{uuid.uuid4().hex[:8]}"
    create = await client.post(
        ORG_PREFIX,
        headers=h,
        json={
            "name": name,
            "parent_id": None,
            "unit_type": "department",
            "code": f"code-{uuid.uuid4().hex[:6]}",
            "sort_order": 5,
        },
    )
    assert create.status_code == 201, create.text
    unit_id = create.json()["id"]
    assert create.json()["name"] == name
    assert create.json()["sort_order"] == 5

    tree1 = await client.get(f"{ORG_PREFIX}/tree", headers=h)
    assert tree1.status_code == 200
    found = _find_unit(tree1.json(), unit_id)
    assert found is not None
    assert found["name"] == name

    patch = await client.patch(
        f"{ORG_PREFIX}/{unit_id}",
        headers=h,
        json={"name": name + " (updated)", "sort_order": 10},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["name"] == name + " (updated)"
    assert patch.json()["sort_order"] == 10

    data = await _init_data()
    viewer_id = data["viewer_id"]

    mem_add = await client.post(
        f"{ORG_PREFIX}/{unit_id}/members",
        headers=h,
        json={"user_id": viewer_id, "role_in_unit": "member"},
    )
    assert mem_add.status_code == 201, mem_add.text

    mem_list = await client.get(f"{ORG_PREFIX}/{unit_id}/members", headers=h)
    assert mem_list.status_code == 200
    ids = {m["user_id"] for m in mem_list.json()}
    assert viewer_id in ids

    mem_del = await client.delete(f"{ORG_PREFIX}/{unit_id}/members/{viewer_id}", headers=h)
    assert mem_del.status_code == 204, mem_del.text

    delete = await client.delete(f"{ORG_PREFIX}/{unit_id}", headers=h)
    assert delete.status_code == 204, delete.text


@pytest.mark.anyio
async def test_invite_with_org_unit_id(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    h = {**manager_headers, "Content-Type": "application/json"}
    data = await _init_data()

    create = await client.post(
        ORG_PREFIX,
        headers=h,
        json={"name": f"InviteDept-{uuid.uuid4().hex[:6]}", "unit_type": "team"},
    )
    assert create.status_code == 201, create.text
    unit_id = create.json()["id"]

    new_email = f"orginv+{uuid.uuid4().hex[:8]}@hostflow.dev"
    invite_resp = await client.post(
        f"{USERS_PREFIX}/invite",
        headers=h,
        json={
            "email": new_email,
            "role": "recruiter",
            "supervisor_id": data["admin_id"],
            "org_unit_id": unit_id,
            "company_ids": [],
            "expires_in_hours": 72,
        },
    )
    assert invite_resp.status_code == 201, invite_resp.text
    body = invite_resp.json()
    assert body.get("org_unit_id") == unit_id
    assert body.get("email") == new_email

    await client.delete(f"{ORG_PREFIX}/{unit_id}", headers=h)


@pytest.mark.anyio
async def test_user_org_units_patch(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    h = {**manager_headers, "Content-Type": "application/json"}
    data = await _init_data()
    viewer_id = data["viewer_id"]

    create = await client.post(
        ORG_PREFIX,
        headers=h,
        json={"name": f"PatchDept-{uuid.uuid4().hex[:6]}", "unit_type": "department"},
    )
    assert create.status_code == 201
    unit_id = create.json()["id"]

    patch = await client.patch(
        f"{USERS_PREFIX}/{viewer_id}/org-units",
        headers=h,
        json={"org_unit_ids": [unit_id]},
    )
    assert patch.status_code == 200, patch.text
    units = patch.json().get("org_units") or []
    assert any(u.get("org_unit_id") == unit_id for u in units)

    clear = await client.patch(
        f"{USERS_PREFIX}/{viewer_id}/org-units",
        headers=h,
        json={"org_unit_ids": []},
    )
    assert clear.status_code == 200

    await client.delete(f"{ORG_PREFIX}/{unit_id}", headers=h)
