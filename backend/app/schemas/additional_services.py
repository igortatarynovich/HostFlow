from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

ServiceUnitLiteral = Literal["piece", "person", "hour", "package"]
ServiceOrderStatusLiteral = Literal[
    "draft",
    "confirmed",
    "in_progress",
    "completed",
    "cancelled",
    "on_hold",
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
    estimated_cost: Decimal = Decimal("0")
    cost_currency: str = Field("PLN", min_length=3, max_length=3)
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
    estimated_cost: Optional[Decimal] = None
    cost_currency: Optional[str] = Field(None, min_length=3, max_length=3)
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
    metrics_orders_count: int = Field(
        0,
        description="Distinct non-cancelled orders that include this catalog service (non-cancelled lines).",
    )
    metrics_revenue_completed: Decimal = Field(
        Decimal("0"),
        description="Sum of line amounts on completed orders (excludes cancelled lines). Mixed currencies are summed numerically.",
    )


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
    estimated_cost: Decimal
    actual_cost: Optional[Decimal] = None
    cost_currency: str
    cost_source: Optional[str] = None
    cost_status: str
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
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    cost_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    cost_source: Optional[str] = None
    cost_status: Optional[str] = None
    vat_rate: Optional[Decimal] = None
    required_documents: Optional[List[str]] = None
    result_document_type: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class ServiceOrderBase(BaseModel):
    candidate_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    company_id: Optional[str] = None
    currency: str = Field("PLN", min_length=3, max_length=3)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    audit: Optional[Dict[str, Any]] = None


class ServiceOrderCreate(ServiceOrderBase):
    requested_by: Optional[str] = None
    items: List[ServiceItemCreate] = Field(default_factory=list)


class ServiceOrderUpdate(BaseModel):
    # Accepts canonical statuses plus legacy aliases (quoted/approved/scheduled/delivered/refunded).
    status: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    audit: Optional[Dict[str, Any]] = None


class ServiceOrderOut(ServiceOrderBase):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v)},
    )

    own_company_id: Optional[str] = None
    id: str
    tenant_id: str
    status: ServiceOrderStatusLiteral
    total_amount: Decimal
    vat_total: Decimal
    requested_by: str
    created_at: datetime
    updated_at: datetime
    items: List[ServiceItemOut] = Field(default_factory=list)

    @computed_field
    def client_id(self) -> Optional[str]:
        return self.company_id

    @model_validator(mode="before")
    @classmethod
    def _coerce_audit(cls, data: Any) -> Any:
        # DB may contain NULL in audit; API should return a stable object.
        if isinstance(data, dict):
            if data.get("audit") is None:
                data["audit"] = {}
            return data
        try:
            audit = getattr(data, "audit", None)
            if audit is None:
                setattr(data, "audit", {})
        except Exception:
            pass
        return data


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
