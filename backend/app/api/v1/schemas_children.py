from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Documents
class DocumentCreate(BaseModel):
    doc_type: str
    file_url: Optional[str] = None
    status: Optional[str] = "pending"
    comment: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class DocumentUpdate(BaseModel):
    doc_type: Optional[str] = None
    file_url: Optional[str] = None
    status: Optional[str] = None
    comment: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class DocumentOut(DocumentCreate):
    id: UUID
    candidate_id: UUID


# Permits
class PermitCreate(BaseModel):
    permit_type: str
    country: Optional[str] = None
    number: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    status: Optional[str] = "requested"
    meta: Dict[str, Any] = Field(default_factory=dict)


class PermitUpdate(BaseModel):
    permit_type: Optional[str] = None
    country: Optional[str] = None
    number: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    status: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class PermitOut(PermitCreate):
    id: UUID
    candidate_id: UUID


# Visa
class VisaCreate(BaseModel):
    visa_type: str
    number: Optional[str] = None
    issued_on: Optional[date] = None
    expires_on: Optional[date] = None
    status: Optional[str] = "planned"
    checkpoints: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)


class VisaUpdate(BaseModel):
    visa_type: Optional[str] = None
    number: Optional[str] = None
    issued_on: Optional[date] = None
    expires_on: Optional[date] = None
    status: Optional[str] = None
    checkpoints: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None


class VisaOut(VisaCreate):
    id: UUID
    candidate_id: UUID


# Tasks
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    completed: Optional[bool] = False
    priority: Optional[str] = "normal"
    assigned_to: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    completed: Optional[bool] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class TaskOut(TaskCreate):
    id: UUID
    candidate_id: UUID
