from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

# === Service Catalog ===


class ServiceCatalogCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True


class ServiceCatalogUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ServiceCatalogOut(BaseModel):
    id: str
    tenant_id: str
    code: str
    name: str
    description: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# === Candidate Services ===


class CandidateServiceCreate(BaseModel):
    service_id: str
    status: str = "assigned"
    price: Optional[float] = None
    currency: Optional[str] = None
    quantity: Optional[int] = 1
    note: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class CandidateServicePatch(BaseModel):
    status: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    quantity: Optional[int] = None
    note: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class CandidateServiceOut(BaseModel):
    id: str
    tenant_id: str
    candidate_id: str
    service_id: str
    service_code: str
    service_name: str
    status: str
    note: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    quantity: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class CandidateServicesList(BaseModel):
    items: List[CandidateServiceOut]
    total: int
    limit: int
    offset: int
