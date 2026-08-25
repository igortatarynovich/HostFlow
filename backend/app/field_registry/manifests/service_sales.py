"""Service sales canonical fields (targeted advertising questionnaire)."""

from __future__ import annotations

from typing import Any

from backend.app.field_registry.constants import ENTITY_LEAD, SERVICE_SALES_MODULE

_PREFIX = "service_sales.targeted_advertising"


def _sales_field(field_code: str, *, field_type: str, name: str) -> dict[str, Any]:
    qualified = f"{_PREFIX}.{field_code}"
    return {
        "qualified_code": qualified,
        "code": field_code.replace(".", "_"),
        "entity_type": ENTITY_LEAD,
        "field_type": field_type,
        "name": name,
        "label_key": f"fields.service_sales_{field_code.replace('.', '_')}",
        "ownership": SERVICE_SALES_MODULE,
        "pii_class": "business" if field_code.startswith("contact_") else None,
        "reference_domain": None,
        "storage": {"kind": "json_path", "path": f"sales_questionnaire.{field_code}"},
        "legacy_aliases": [field_code],
        "default_section": "questionnaire",
    }


def service_sales_targeted_advertising_fields() -> list[dict[str, Any]]:
    rows: list[tuple[str, str, str]] = [
        ("need_type", "single_select", "Need type"),
        ("primary_outcome", "single_select", "Primary outcome"),
        ("recruitment_roles", "multi_select", "Recruitment roles"),
        ("recruitment_other_role", "text", "Other recruitment role"),
        ("recruitment_headcount", "single_select", "Recruitment headcount"),
        ("work_location_country", "single_select", "Work location country"),
        ("work_location_city", "text", "Work location city"),
        ("application_channel", "single_select", "Application channel"),
        ("job_posting_ready", "single_select", "Job posting readiness"),
        ("recruitment_materials", "multi_select", "Recruitment materials"),
        ("promotion_subject", "single_select", "Promotion subject"),
        ("industry", "single_select", "Industry"),
        ("target_audience_description", "textarea", "Target audience description"),
        ("qualified_lead_definition", "textarea", "Qualified lead definition"),
        ("client_geo_scope", "single_select", "Client geography scope"),
        ("client_geo_detail", "text", "Client geography detail"),
        ("conversion_destination", "single_select", "Conversion destination"),
        ("offer_ready", "single_select", "Offer readiness"),
        ("marketing_materials", "multi_select", "Marketing materials"),
        ("prior_ads_experience", "single_select", "Prior ads experience"),
        ("monthly_ad_budget", "single_select", "Monthly ad budget"),
        ("start_timeline", "single_select", "Start timeline"),
        ("decision_maker", "single_select", "Decision maker"),
        ("contact_full_name", "text", "Contact full name"),
        ("contact_company_name", "text", "Contact company name"),
        ("contact_phone", "phone_e164", "Contact phone"),
        ("contact_email", "email", "Contact email"),
        ("contact_website", "text", "Contact website"),
        ("additional_notes", "textarea", "Additional notes"),
    ]
    return [_sales_field(code, field_type=ftype, name=name) for code, ftype, name in rows]


def service_sales_module_manifest() -> dict[str, Any]:
    return {
        "module": SERVICE_SALES_MODULE,
        "registry_version": "field_registry_v1",
        "canonical_fields": service_sales_targeted_advertising_fields(),
        "card_layouts": [],
    }
