"""Typed JSON payloads for company_module_settings.settings_json (ADR-005)."""

from __future__ import annotations

from typing import Any, Literal, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = (
    "HrModuleSettingsV1",
    "RecruitmentModuleSettingsV1",
    "FleetModuleSettingsV1",
    "ServicesModuleSettingsV1",
    "FinanceModuleSettingsV1",
    "LeadLifecycleEmailPolicyV1",
    "LeadLifecycleOpsPurposeV1",
    "MODULE_SETTINGS_MODEL_V1",
    "normalize_company_module_settings_json",
)


class LeadLifecycleOpsPurposeV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    template_ref: Optional[str] = Field(default=None, max_length=128)


class LeadLifecycleEmailPolicyV1(BaseModel):
    """ADR-033 — company-scoped lead lifecycle email policy."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    rodo_send_mode: Literal["manual", "auto_on_lead_created", "auto_on_first_action"] = "auto_on_lead_created"
    rodo_template_ref: Optional[str] = Field(default=None, max_length=128)

    @field_validator("rodo_send_mode", mode="before")
    @classmethod
    def _platform_rodo_send_mode(cls, _value: Any) -> str:
        return "auto_on_lead_created"
    ops_enabled: bool = False
    application_received: LeadLifecycleOpsPurposeV1 = Field(default_factory=LeadLifecycleOpsPurposeV1)
    rejection: LeadLifecycleOpsPurposeV1 = Field(default_factory=LeadLifecycleOpsPurposeV1)
    moving_forward: LeadLifecycleOpsPurposeV1 = Field(default_factory=LeadLifecycleOpsPurposeV1)
    channels: list[str] = Field(default_factory=lambda: ["email"])


class HrModuleSettingsV1(BaseModel):
    """HR module settings document (versioned)."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    employee_pipeline_funnel_id: Optional[str] = Field(
        default=None,
        max_length=36,
        description="Optional funnel id for employee / HR pipeline (when introduced end-to-end).",
    )
    employment_template_ids: Optional[list[str]] = Field(default=None)
    hr_document_template_ids: Optional[list[str]] = Field(default=None)
    contract_template_ids: Optional[list[str]] = Field(default=None)
    zus_checklist: Optional[list[dict[str, Any]]] = Field(default=None)
    work_permit_rules: Optional[dict[str, Any]] = Field(default=None)
    hr_assignment_rules: Optional[dict[str, Any]] = Field(default=None)


class RecruitmentModuleSettingsV1(BaseModel):
    """Recruitment — pipelines, sources, templates, handoff (company-scoped)."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    default_candidate_funnel_id: Optional[str] = Field(default=None, max_length=36)
    lead_source_configs: Optional[list[dict[str, Any]]] = Field(default=None)
    vacancy_template_ids: Optional[list[str]] = Field(default=None)
    candidate_document_template_ids: Optional[list[str]] = Field(default=None)
    handoff_rules: Optional[dict[str, Any]] = Field(default=None)
    recruiter_assignment_rules: Optional[dict[str, Any]] = Field(default=None)
    lead_lifecycle_email_v1: Optional[LeadLifecycleEmailPolicyV1] = Field(
        default=None,
        description="ADR-033 company SoT for lead RODO + ops lifecycle emails.",
    )


class FleetModuleSettingsV1(BaseModel):
    """Fleet — vehicle types, templates, assignments, inspections (company-scoped)."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    vehicle_type_codes: Optional[list[str]] = Field(default=None)
    vehicle_document_template_ids: Optional[list[str]] = Field(default=None)
    handover_checklist_template_ids: Optional[list[str]] = Field(default=None)
    assignment_rules: Optional[dict[str, Any]] = Field(default=None)
    damage_report_settings: Optional[dict[str, Any]] = Field(default=None)
    inspection_template_ids: Optional[list[str]] = Field(default=None)


class ServicesModuleSettingsV1(BaseModel):
    """Services / orders — catalog, statuses, workflows (company-scoped)."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    service_catalog_snapshot: Optional[dict[str, Any]] = Field(
        default=None,
        description="References or embedded catalog config; refine when catalog is normalized.",
    )
    order_status_codes: Optional[list[str]] = Field(default=None)
    service_template_ids: Optional[list[str]] = Field(default=None)
    delivery_workflows: Optional[dict[str, Any]] = Field(default=None)
    pricing_rules: Optional[dict[str, Any]] = Field(default=None)


class FinanceModuleSettingsV1(BaseModel):
    """Finance — invoicing, VAT, terms (company-scoped)."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    invoice_number_prefix: Optional[str] = Field(default=None, max_length=64)
    invoice_number_next: Optional[int] = Field(default=None, ge=0)
    vat_rates: Optional[dict[str, Any]] = Field(default=None)
    payment_terms_days: Optional[int] = Field(default=None, ge=0)
    billing_rules: Optional[dict[str, Any]] = Field(default=None)
    payment_status_codes: Optional[list[str]] = Field(default=None)
    correction_rules: Optional[dict[str, Any]] = Field(default=None)


MODULE_SETTINGS_MODEL_V1: dict[str, Type[BaseModel]] = {
    "hr": HrModuleSettingsV1,
    "recruitment": RecruitmentModuleSettingsV1,
    "fleet": FleetModuleSettingsV1,
    "services": ServicesModuleSettingsV1,
    "finance": FinanceModuleSettingsV1,
}


def normalize_company_module_settings_json(module_key: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and return JSON-serializable settings for storage. Raises ValidationError."""
    model = MODULE_SETTINGS_MODEL_V1.get(module_key)
    if model is not None:
        return model.model_validate(raw).model_dump(mode="json")
    return dict(raw)
