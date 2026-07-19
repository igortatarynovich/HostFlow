"""Stage 2B — unified backend module gate (ADR-023 §3.4).

Check order (hostname is never an authorization source):
1. owning module for the endpoint (caller / path registry)
2. tenant module entitlement
3. company module enablement (when company context present)
4. user access to that company (when company context present)
5. user module access (role matrix / overrides)
6. action permission (read vs write)
7. object scope — remains on entity ACL helpers (candidates/employees/…);
   this gate does not replace object ownership checks.
"""
from __future__ import annotations

from typing import Literal, Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant
from backend.app.module_registry.resolver import is_module_installed
from backend.app.modules.http_module_ownership import GATE_MODULE_KEYS, resolve_http_module_owner
from backend.app.services.access import list_user_access
from backend.app.services.company_module_access import company_allows_module

ModuleAction = Literal["read", "write"]

_ADMIN_ROLES = frozenset(
    {
        Role.superadmin.value,
        Role.administrator.value,
        "admin",
        "owner",
    }
)

# Map gate module → role_matrix / tenant.settings.modules key used for user access.
_USER_MATRIX_KEYS: dict[str, tuple[str, ...]] = {
    "recruitment": ("recruitment", "candidates", "leads", "vacancies"),
    "hr": ("hr",),
    "sales": ("sales", "companies", "client_portal", "services"),
    "fleet": ("fleet",),
    "finance": ("finance",),
}


def action_from_http_method(method: str) -> ModuleAction:
    m = (method or "GET").upper()
    if m in {"GET", "HEAD", "OPTIONS"}:
        return "read"
    return "write"


def extract_company_id_from_request(request: Request) -> str | None:
    q = request.query_params.get("company_id")
    if q and str(q).strip():
        return str(q).strip()
    header = (
        request.headers.get("X-Company-Id")
        or request.headers.get("x-company-id")
        or ""
    ).strip()
    if header:
        return header
    # Path patterns: /companies/{id}/… is platform; module routes rarely embed company.
    return None


async def enforce_module_gate(
    *,
    db: AsyncSession,
    tenant_id: str,
    ctx: UserCtx,
    module_key: str,
    action: ModuleAction = "read",
    company_id: str | None = None,
    request_path: str | None = None,
) -> None:
    """Raise 403 when any Stage 2B entitlement layer denies access."""
    key = str(module_key or "").strip().lower()
    if key not in GATE_MODULE_KEYS:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unknown module gate key: {module_key}",
        )

    # Optional consistency: if path is known, it must match declared owner.
    if request_path:
        path_owner = resolve_http_module_owner(request_path)
        if path_owner is not None and path_owner != key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Module path ownership mismatch",
            )

    role = (ctx.role or "").strip().lower()
    if role == Role.superadmin.value:
        return

    tenant = await db.get(Tenant, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # 2) Tenant module entitlement — settings.modules is the product SSOT toggled by
    # /settings/team/modules (registry installation alone must not override an explicit off/on).
    snapshot = tenant_service.get_module_settings_snapshot(tenant)
    if key in snapshot:
        tenant_on = bool(snapshot.get(key))
    else:
        tenant_on = await is_module_installed(db, tenant_id, key)
    if not tenant_on:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{key.capitalize()} module is disabled for this workspace",
        )

    company: Company | None = None
    cid = str(company_id or "").strip() or None
    if cid:
        company = await db.get(Company, cid)
        if company is None or str(company.tenant_id) != str(tenant_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        # 3) Company module enablement
        if not company_allows_module(tenant, company, key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{key.capitalize()} module is disabled for this company",
            )

        # 4) User ↔ company access (admins bypass)
        if role not in _ADMIN_ROLES and role != Role.supervisor.value:
            access_rows = await list_user_access(db, tenant_id=str(tenant_id), user_id=str(ctx.sub))
            allowed_ids = {str(row.company_id) for row in access_rows}
            # Empty ACL table historically means «no restriction» for many roles;
            # only enforce when the tenant has at least one ACL row for this user
            # OR when the user is a client_* role (always scoped).
            if allowed_ids:
                if cid not in allowed_ids:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No access to this company",
                    )
            elif role in {
                Role.client_manager.value,
                Role.client_processor.value,
                "client",
            }:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No access to this company",
                )

    # 5–6) User module access + action (role matrix / overrides)
    if role not in _ADMIN_ROLES:
        perms = tenant_service.get_effective_role_module_permissions(
            tenant,
            role=role,
            user_id=str(ctx.sub),
        )
        matrix_keys = _USER_MATRIX_KEYS.get(key, (key,))
        visible = False
        editable = False
        for mk in matrix_keys:
            cell = perms.get(mk) or {}
            visible = visible or bool(cell.get("visible"))
            editable = editable or bool(cell.get("editable"))
        # If product key missing from matrix entirely, fall back to tenant module on
        # (legacy tenants before matrix keys were expanded).
        if not any(mk in perms for mk in matrix_keys):
            visible = True
            editable = role in {
                Role.supervisor.value,
                Role.recruiter.value,
                Role.hr_officer.value,
                Role.compliance_officer.value,
                Role.client_manager.value,
                "fleet_manager",
            }

        if action == "read" and not visible:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No {key} module access for this user",
            )
        if action == "write" and not editable:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No {key} write permission for this user",
            )


def require_module_gate(
    module_key: str,
    *,
    action: ModuleAction | None = None,
):
    """FastAPI dependency: enforce Stage 2B gate for a declared module owner."""

    async def _dep(
        request: Request,
        ctx: UserCtx = Depends(get_current_user),
        db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    ) -> UserCtx:
        db, tenant_uuid = db_tenant
        resolved_action = action or action_from_http_method(request.method)
        company_id = extract_company_id_from_request(request)
        await enforce_module_gate(
            db=db,
            tenant_id=str(tenant_uuid),
            ctx=ctx,
            module_key=module_key,
            action=resolved_action,
            company_id=company_id,
            request_path=request.url.path,
        )
        return ctx

    return _dep


# Back-compat thin wrappers (existing imports).
async def require_hr_workforce_module_access(
    request: Request,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> UserCtx:
    db, tenant_uuid = db_tenant
    await enforce_module_gate(
        db=db,
        tenant_id=str(tenant_uuid),
        ctx=ctx,
        module_key="hr",
        action=action_from_http_method(request.method),
        company_id=extract_company_id_from_request(request),
        request_path=request.url.path,
    )
    return ctx


async def require_fleet_module_access(
    request: Request,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> UserCtx:
    db, tenant_uuid = db_tenant
    await enforce_module_gate(
        db=db,
        tenant_id=str(tenant_uuid),
        ctx=ctx,
        module_key="fleet",
        action=action_from_http_method(request.method),
        company_id=extract_company_id_from_request(request),
        request_path=request.url.path,
    )
    return ctx
