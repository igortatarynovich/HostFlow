"""ZUS workspace MVP — task queue payloads (no ZUS API)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ZusWorkspaceTaskCreate(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=36)
    workspace_lane: str = Field(..., max_length=32)
    task_kind: str = Field(..., min_length=1, max_length=64)
    title: str = Field(default="", max_length=256)
    form_kind: Optional[str] = Field(default=None, max_length=32)
    form_status: Optional[str] = Field(default=None, max_length=32)
    status: str = Field(default="open", max_length=32)
    due_at: Optional[datetime] = None
    assigned_hr_user_id: Optional[str] = Field(default=None, max_length=36)
    export_status: Optional[str] = Field(default=None, max_length=32)
    checklist_json: Optional[Any] = None
    notes: Optional[str] = None


class ZusWorkspaceTaskPatch(BaseModel):
    workspace_lane: Optional[str] = Field(default=None, max_length=32)
    task_kind: Optional[str] = Field(default=None, max_length=64)
    title: Optional[str] = Field(default=None, max_length=256)
    form_kind: Optional[str] = Field(default=None, max_length=32)
    form_status: Optional[str] = Field(default=None, max_length=32)
    status: Optional[str] = Field(default=None, max_length=32)
    due_at: Optional[datetime] = None
    assigned_hr_user_id: Optional[str] = Field(default=None, max_length=36)
    export_status: Optional[str] = Field(default=None, max_length=32)
    checklist_json: Optional[Any] = None
    notes: Optional[str] = None


class ZusWorkspaceTaskOut(BaseModel):
    id: str
    tenant_id: str
    employee_id: str
    employee_display_name: str = ""
    workspace_lane: str
    task_kind: str
    form_kind: Optional[str] = None
    form_status: Optional[str] = None
    status: str
    due_at: Optional[datetime] = None
    assigned_hr_user_id: Optional[str] = None
    export_status: Optional[str] = None
    checklist_json: Optional[Any] = None
    title: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ZusWorkspaceTaskPageOut(BaseModel):
    items: list[ZusWorkspaceTaskOut]
    total: int
