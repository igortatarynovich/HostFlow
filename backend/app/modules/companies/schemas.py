from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Dict, List, Literal, Optional, Set
from uuid import UUID, uuid4

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
except ImportError:  # pragma: no cover - Pydantic < 2 compatibility
    from pydantic import BaseModel, BaseConfig, Field, validator, root_validator

    field_validator = None  # type: ignore
    model_validator = None  # type: ignore

    def field_validator(*fields, **kwargs):  # type: ignore[misc]
        decorator = validator(*fields, **kwargs)

        def _wrapper(func):
            if isinstance(func, classmethod):
                func = func.__func__  # type: ignore[attr-defined]
            return decorator(func)

        return _wrapper

    def model_validator(*, mode: str):  # type: ignore[misc]
        if mode != "after":
            raise NotImplementedError("Only mode='after' supported in compatibility mode")

        def _decorator(func):
            if isinstance(func, classmethod):
                func = func.__func__  # type: ignore[attr-defined]

            @root_validator(pre=False)
            def _wrapper(cls, values):  # type: ignore
                result = func(cls, values)
                return result if result is not None else values

            return _wrapper

        return _decorator

    class ConfigDict(dict):  # type: ignore[misc]
        def __init__(self, **kwargs):
            super().__init__(**kwargs)


class CompanyMutableFields(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    tax_id: Optional[str] = Field(None, max_length=64)
    phone: Optional[str] = Field(None, max_length=64)
    email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=2000)
    is_archived: Optional[bool] = None
    country_code: Optional[str] = Field(None, max_length=2)
    country: Optional[str] = Field(None, max_length=64)
    city: Optional[str] = Field(None, max_length=128)
    address: Optional[str] = Field(None, max_length=255)
    contacts: Optional[dict[str, Any]] = None
    extra: Optional[dict[str, Any]] = None

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value) != 2:
            raise ValueError("country_code must be exactly 2 characters")
        return value


class CompanyCreate(CompanyMutableFields):
    name: str = Field(..., max_length=255)


class CompanyUpdate(CompanyMutableFields):
    pass


class CompanyBase(CompanyMutableFields):
    name: str = Field(..., max_length=255)
    is_archived: bool = False


class CompanyOut(CompanyBase):
    id: UUID
    tenant_id: UUID
    contacts: dict[str, Any] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Address(BaseModel):
    country: Optional[str] = Field(None, max_length=64)
    city: Optional[str] = Field(None, max_length=128)
    street: Optional[str] = Field(None, max_length=255)
    zip: Optional[str] = Field(None, max_length=32)
    house: Optional[str] = Field(None, max_length=32)
    apartment: Optional[str] = Field(None, max_length=32)
    region: Optional[str] = Field(None, max_length=64)


class Representative(BaseModel):
    id: Optional[UUID] = None
    full_name: str = Field(..., max_length=255)
    role: Optional[str] = Field(None, max_length=64)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=64)


class LegalProfile(BaseModel):
    reg_no: Optional[str] = Field(None, max_length=64)
    vat_eu: Optional[str] = Field(None, max_length=32)
    established_at: Optional[date] = None
    transport_license_number: Optional[str] = Field(None, max_length=64)
    insurance_policy_no: Optional[str] = Field(None, max_length=64)
    registered_address: Optional[Address] = None
    operational_address: Optional[Address] = None
    authorized_representatives: List[Representative] = Field(default_factory=list)


def _normalize_iban(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum()).upper()


def _validate_iban_checksum(value: str) -> None:
    clean = _normalize_iban(value)
    if not (15 <= len(clean) <= 34):
        raise ValueError("IBAN length must be between 15 and 34 characters")
    rearranged = clean[4:] + clean[:4]
    remainder = 0
    for ch in rearranged:
        if ch.isdigit():
            remainder = (remainder * 10 + int(ch)) % 97
        else:
            converted = ord(ch) - 55  # A=10
            for digit in str(converted):
                remainder = (remainder * 10 + int(digit)) % 97
    if remainder != 1:
        raise ValueError("IBAN checksum validation failed")


class BankAccount(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    bank_name: Optional[str] = Field(None, max_length=255)
    iban: str = Field(..., max_length=64)
    swift_bic: Optional[str] = Field(None, max_length=11)
    country: Optional[str] = Field(None, max_length=64)
    label: Optional[str] = Field(None, max_length=64)
    is_primary: bool = False

    @field_validator("iban")
    @classmethod
    def validate_iban(cls, value: str) -> str:
        if not value:
            raise ValueError("IBAN is required")
        _validate_iban_checksum(value)
        return _normalize_iban(value)

    @field_validator("swift_bic")
    @classmethod
    def validate_swift(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip().upper()
        if cleaned and len(cleaned) not in (8, 11):
            raise ValueError("SWIFT/BIC must be 8 or 11 characters")
        if cleaned and not cleaned.isalnum():
            raise ValueError("SWIFT/BIC may only contain letters and digits")
        return cleaned or None


class EInvoicePeppol(BaseModel):
    participant_id: Optional[str] = Field(None, max_length=100)
    scheme: Optional[str] = Field(None, max_length=32)


class BillingProfile(BaseModel):
    default_currency: Optional[str] = Field(None, max_length=3)
    payment_terms_days: Optional[int] = Field(None, ge=1, le=120)
    invoice_email: Optional[str] = Field(None, max_length=255)
    billing_address: Optional[Address] = None
    einvoice_peppol: Optional[EInvoicePeppol] = None
    bank_accounts: List[BankAccount] = Field(default_factory=list)

    @field_validator("default_currency")
    @classmethod
    def validate_currency(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        upper = value.upper()
        if len(upper) != 3:
            raise ValueError("Currency code must be ISO 4217 (3 letters)")
        return upper

    @field_validator("invoice_email")
    @classmethod
    def validate_invoice_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if "@" not in value:
            raise ValueError("Invoice email must contain '@'")
        return value

    @model_validator(mode="after")
    def ensure_single_primary(cls, model: "BillingProfile") -> "BillingProfile":
        primary_count = sum(1 for account in model.bank_accounts if account.is_primary)
        if primary_count > 1:
            raise ValueError("Only one bank account can be marked as primary")
        return model


class Contact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: Optional[str] = Field(None, max_length=32)
    full_name: str = Field(..., max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=64)
    is_primary: bool = False
    is_portal_user: bool = False

    ALLOWED_ROLES: ClassVar[Set[str]] = {
        "OWNER",
        "ACC",
        "HR",
        "FM",
        "OPS",
        "LEGAL",
        "DISPATCH",
        "SALES",
        "SUPPORT",
        "CEO",
    }

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().upper()
        if not normalized:
            return None
        if normalized not in cls.ALLOWED_ROLES:
            raise ValueError(f"Unsupported contact role '{value}'")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if "@" not in value:
            raise ValueError("Contact email must contain '@'")
        return value


class OperationsProfile(BaseModel):
    fleet_tractors: Optional[int] = Field(None, ge=0)
    fleet_intl_perc: Optional[int] = Field(None, ge=0, le=100)
    fleet_local_perc: Optional[int] = Field(None, ge=0, le=100)
    drivers_total: Optional[int] = Field(None, ge=0)
    has_adr_operations: bool = False
    work_modes: List[Literal["UOP", "B2B", "LEASE"]] = Field(default_factory=list)
    trailer_types: Dict[str, Optional[int]] = Field(default_factory=dict)
    lanes: Dict[str, List[str]] = Field(default_factory=lambda: {"origins": [], "destinations": []})
    cargo_types: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    preferred_nationalities: List[str] = Field(default_factory=list)


class ComplianceProfile(BaseModel):
    fin_check_status: Literal["pending", "pass", "fail", "manual_review"] = "pending"
    aml_required: bool = False
    iso9001: bool = False
    doc_valid_until: Optional[date] = None
    last_compliance_check_at: Optional[datetime] = None


class PortalRole(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    full_name: str = Field(..., max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(None, max_length=64)


class PortalProfile(BaseModel):
    enabled: bool = False
    url: Optional[str] = Field(None, max_length=255)
    last_sync_at: Optional[datetime] = None
    portal_roles: List[PortalRole] = Field(default_factory=list)
    permissions: Optional[str] = None


class WebhookEndpoint(BaseModel):
    event: str = Field(..., max_length=64)
    target: str = Field(..., max_length=512)


class BrandingInfo(BaseModel):
    logo_url: Optional[str] = Field(None, max_length=512)
    primary_color: Optional[str] = Field(None, max_length=16)


class IntegrationsProfile(BaseModel):
    provider_ids: List[str] = Field(default_factory=list)
    webhooks: List[WebhookEndpoint] = Field(default_factory=list)
    branding: Optional[BrandingInfo] = None
    external_id: Optional[str] = Field(None, max_length=128)
    source: Optional[str] = Field(None, max_length=64)
    synced_at: Optional[datetime] = None


class ContractRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., max_length=255)
    status: Optional[str] = Field(None, max_length=64)
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None
    reference: Optional[str] = Field(None, max_length=128)
    code: Optional[str] = Field(None, max_length=64)


class OrderRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., max_length=255)
    status: Optional[str] = Field(None, max_length=64)
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None
    required_drivers: Optional[int] = Field(None, ge=0)
    hired_drivers: Optional[int] = Field(None, ge=0)
    client_reference: Optional[str] = Field(None, max_length=128)
    code: Optional[str] = Field(None, max_length=64)


class CompanyProfile(BaseModel):
    legal: Optional[LegalProfile] = None
    billing: Optional[BillingProfile] = None
    operations: Optional[OperationsProfile] = None
    compliance: Optional[ComplianceProfile] = None
    client_portal: Optional[PortalProfile] = None
    integrations: Optional[IntegrationsProfile] = None
    contracts: List[ContractRecord] = Field(default_factory=list)
    company_orders: List[OrderRecord] = Field(default_factory=list)


class CompanyReadiness(BaseModel):
    company_id: UUID
    has_legal: bool
    has_primary_contact: bool
    has_primary_bank: bool
    fin_check_status: str
    billing_ready: bool
    compliance_valid: bool
    client_portal_enabled: bool
    readiness_score: Optional[float] = None
    readiness_state: Optional[str] = None
