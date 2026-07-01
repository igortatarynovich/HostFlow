from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


OrgUnitType = Literal["division", "department", "team", "cost_center", "other"]


class OrgUnitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: str | None = None
    unit_type: str = Field(default="department", max_length=32)
    code: str | None = Field(default=None, max_length=64)
    leader_user_id: str | None = None
    sort_order: int = 0
    meta: dict[str, Any] = Field(default_factory=dict)


class OrgUnitPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: str | None = None
    unit_type: str | None = Field(default=None, max_length=32)
    code: str | None = Field(default=None, max_length=64)
    leader_user_id: str | None = None
    sort_order: int | None = None
    meta: dict[str, Any] | None = None


class OrgUnitMemberAdd(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=36)
    role_in_unit: str = Field(default="member", max_length=32)


class UserOrgUnitsAssign(BaseModel):
    org_unit_ids: list[str] = Field(default_factory=list)


class OrgUnitImportRow(BaseModel):
    """Row for merge-by-code import (HRIS / backup). Every row must have a unique `code`."""

    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    parent_code: str | None = None
    unit_type: str = Field(default="department", max_length=32)
    sort_order: int = 0
    leader_user_id: str | None = None
    meta: dict[str, Any] | None = None


class OrgStructureImport(BaseModel):
    version: Literal[1] = 1
    units: list[OrgUnitImportRow] = Field(default_factory=list)
