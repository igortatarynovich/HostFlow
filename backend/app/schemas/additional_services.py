from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ServiceUnitLiteral = Literal["piece", "person", "hour", "package"]
ServiceOrderStatusLiteral = Literal[
    "draft",
    "quoted",
    "approved",
    "scheduled",
    "in_progress",
    "delivered",
    "cancelled",
    "refunded",
]
ServiceItemStatusLiteral = Literal[
    "pending",
    "scheduled",
    "in_progress",
    "delivered",
    "cancelled",
    "quoted",
]
ServiceScheduleStatusLiteral = Literal[
    "reserved",
    "confirmed",
    "completed",
    "no_show",
    "cancelled",
]


class ServiceBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    unit: ServiceUnitLiteral = "piece"
    base_price: Decimal = Decimal("0")
    currency: str = Field("PLN", min_length=3, max_length=3)
    vat_rate: Decimal = Decimal("23")
    requires_schedule: bool = False
    requires_candidate: bool = False
    result_document_type: Optional[str] = None
    requires_documents: Optional[List[str]] = None
    sla_hours: Optional[int] = None
    is_active: bool = True
    meta: Dict[str, Any] = Field(default_factory=dict)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[ServiceUnitLiteral] = None
    base_price: Optional[Decimal] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    vat_rate: Optional[Decimal] = None
    requires_schedule: Optional[bool] = None
    requires_candidate: Optional[bool] = None
    result_document_type: Optional[str] = None
    requires_documents: Optional[List[str]] = None
    sla_hours: Optional[int] = None
    is_active: Optional[bool] = None
    meta: Optional[Dict[str, Any]] = None


class ServiceOut(ServiceBase):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v)},
    )

    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime


class ServiceAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    item_id: str
    file_id: str
    label: Optional[str] = None
    created_at: datetime


class ServiceScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    item_id: str
    provider: Optional[str] = None
    slot_start: Optional[datetime] = None
    slot_end: Optional[datetime] = None
    location: Optional[str] = None
    status: ServiceScheduleStatusLiteral
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ServiceItemOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v)},
    )

    id: str
    tenant_id: str
    order_id: str
    service_id: str
    qty: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    amount: Decimal
    status: ServiceItemStatusLiteral
    required_documents: Optional[List[str]] = None
    result_document_type: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    service: Optional[ServiceOut] = None
    schedules: List[ServiceScheduleOut] = Field(default_factory=list)
    attachments: List[ServiceAttachmentOut] = Field(default_factory=list)


class ServiceItemCreate(BaseModel):
    service_id: Optional[str] = None
    service_code: Optional[str] = None
    qty: Decimal = Decimal("1")
    unit_price: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    required_documents: Optional[List[str]] = None
    result_document_type: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class ServiceOrderBase(BaseModel):
    candidate_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    company_id: Optional[str] = None
    currency: str = Field("PLN", min_length=3, max_length=3)
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    audit: Dict[str, Any] = Field(default_factory=dict)


class ServiceOrderCreate(ServiceOrderBase):
    requested_by: Optional[str] = None
    items: List[ServiceItemCreate] = Field(default_factory=list)


class ServiceOrderUpdate(BaseModel):
    status: Optional[ServiceOrderStatusLiteral] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    audit: Optional[Dict[str, Any]] = None


class ServiceOrderOut(ServiceOrderBase):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v)},
    )

    id: str
    tenant_id: str
    status: ServiceOrderStatusLiteral
    total_amount: Decimal
    vat_total: Decimal
    requested_by: str
    created_at: datetime
    updated_at: datetime
    items: List[ServiceItemOut] = Field(default_factory=list)


class ServiceScheduleCreate(BaseModel):
    provider: Optional[str] = None
    slot_start: Optional[datetime] = None
    slot_end: Optional[datetime] = None
    location: Optional[str] = None
    status: ServiceScheduleStatusLiteral = "reserved"
    meta: Optional[Dict[str, Any]] = None


class ServiceScheduleUpdate(BaseModel):
    provider: Optional[str] = None
    slot_start: Optional[datetime] = None
    slot_end: Optional[datetime] = None
    location: Optional[str] = None
    status: Optional[ServiceScheduleStatusLiteral] = None
    meta: Optional[Dict[str, Any]] = None


class ServiceAttachmentCreate(BaseModel):
    file_id: str
    label: Optional[str] = None


class ResultDocumentPayload(BaseModel):
    document_type: str
    number: Optional[str] = None
    status: str = "approved"
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    file_id: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class ServiceItemDeliverPayload(BaseModel):
    status: Optional[ServiceItemStatusLiteral] = "delivered"
    result_document: Optional[ResultDocumentPayload] = None
    attachments: List[ServiceAttachmentCreate] = Field(default_factory=list)
    meta: Optional[Dict[str, Any]] = None


class ServiceOrderSummary(BaseModel):
    order: ServiceOrderOut
    blocking_items: List[ServiceItemOut] = Field(default_factory=list)
    missing_documents: Dict[str, List[str]] = Field(default_factory=dict)
