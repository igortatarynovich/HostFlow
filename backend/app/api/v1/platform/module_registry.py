"""Read-only Module Registry API (P1)."""

from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user, require_roles
from backend.app.auth.hiring_workspace_roles import HIRING_CANDIDATE_PROFILE_READ_ROLES
from backend.app.db.deps import get_db_with_tenant
from backend.app.module_registry.resolver import is_module_installed, list_installed_modules

router = APIRouter(
    prefix="/platform/module-registry",
    tags=["module-registry"],
    redirect_slashes=False,
)


class ModuleCapabilityOut(BaseModel):
    id: str
    module_code: str
    capability_code: str
    kind: str
    display_name: str
    description: Optional[str] = None
    default_enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class ModuleDependencyOut(BaseModel):
    id: str
    module_code: str
    dependency_module_code: str
    dependency_kind: str
    capability_code: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)


class InstalledModuleOut(BaseModel):
    id: str
    module_code: str
    kind: str
    display_name: str
    owner: str
    status: str
    registry_version: str
    manifest: dict[str, Any] = Field(default_factory=dict)
    is_system: bool = True
    tenant_id: str
    installation_state: str
    installation_source: str
    installed: bool
    settings_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    capabilities: List[ModuleCapabilityOut] = Field(default_factory=list)
    dependencies: List[ModuleDependencyOut] = Field(default_factory=list)


class InstalledModuleListOut(BaseModel):
    items: List[InstalledModuleOut]
    count: int


class ModuleInstalledOut(BaseModel):
    module_code: str
    installed: bool


@router.get("/installed-modules", response_model=InstalledModuleListOut)
async def get_installed_modules(
    include_capabilities: bool = Query(default=True),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _: None = Depends(require_roles(*HIRING_CANDIDATE_PROFILE_READ_ROLES)),
    __user=Depends(get_current_user),
) -> InstalledModuleListOut:
    db, tenant_uuid = db_tenant
    items = await list_installed_modules(
        db,
        tenant_id=str(tenant_uuid),
        include_capabilities=include_capabilities,
    )
    return InstalledModuleListOut(
        items=[InstalledModuleOut.model_validate(row) for row in items],
        count=len(items),
    )


@router.get("/installed-modules/{module_code}/installed", response_model=ModuleInstalledOut)
async def get_module_installed(
    module_code: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _: None = Depends(require_roles(*HIRING_CANDIDATE_PROFILE_READ_ROLES)),
    __user=Depends(get_current_user),
) -> ModuleInstalledOut:
    db, tenant_uuid = db_tenant
    installed = await is_module_installed(db, str(tenant_uuid), module_code)
    return ModuleInstalledOut(module_code=module_code, installed=installed)
