"""Service sales canonical fields (targeted advertising questionnaire)."""

from __future__ import annotations

from typing import Any

from backend.app.field_registry.constants import ENTITY_LEAD, SERVICE_SALES_MODULE

_PREFIX = "service_sales.targeted_advertising"


def _sales_field(
    field_code: str,
    *,
    field_type: str,
    name: str,
    reference_domain: str | None = None,
    reference_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    qualified = f"{_PREFIX}.{field_code}"
    row: dict[str, Any] = {
        "qualified_code": qualified,
        "code": field_code.replace(".", "_"),
        "entity_type": ENTITY_LEAD,
        "field_type": field_type,
        "name": name,
        "label_key": f"fields.service_sales_{field_code.replace('.', '_')}",
        "ownership": SERVICE_SALES_MODULE,
        "pii_class": "business" if field_code.startswith("contact_") else None,
        "reference_domain": reference_domain,
        "storage": {"kind": "json_path", "path": f"sales_questionnaire.{field_code}"},
        "legacy_aliases": [field_code],
        "default_section": "questionnaire",
    }
    if reference_meta:
        row["reference_meta"] = reference_meta
    return row


def service_sales_targeted_advertising_fields() -> list[dict[str, Any]]:
    country_filter = {"depends_on_field": f"{_PREFIX}.work_location_country", "query_param": "country"}
    client_country_filter = {"depends_on_field": f"{_PREFIX}.client_geo_country", "query_param": "country"}

    rows: list[dict[str, Any]] = [
        _sales_field("need_type", field_type="single_select", name="Audience type"),
        # Legacy fields kept for stored submissions — hidden from new presentation
        _sales_field("primary_outcome", field_type="single_select", name="Primary outcome"),
        _sales_field("promotion_subject", field_type="single_select", name="Promotion subject"),
        _sales_field("industry", field_type="single_select", name="Industry"),
        _sales_field("client_geo_scope", field_type="single_select", name="Client geography scope"),
        _sales_field("client_geo_detail", field_type="text", name="Client geography detail"),
        _sales_field("application_channel", field_type="single_select", name="Application channel"),
        _sales_field("offer_ready", field_type="single_select", name="Offer readiness"),
        _sales_field("prior_ads_experience", field_type="single_select", name="Prior ads experience"),
        _sales_field("monthly_ad_budget", field_type="single_select", name="Monthly ad budget"),
        _sales_field("start_timeline", field_type="single_select", name="Start timeline"),
        _sales_field("decision_maker", field_type="single_select", name="Decision maker"),
        _sales_field("contact_website", field_type="text", name="Contact website"),
        # Recruitment branch
        _sales_field("recruitment_roles", field_type="multi_select", name="Professions", reference_domain="professions"),
        _sales_field("recruitment_other_role", field_type="text", name="Custom profession"),
        _sales_field("recruitment_headcount", field_type="single_select", name="Headcount"),
        _sales_field("work_location_country", field_type="single_select", name="Work country", reference_domain="countries"),
        _sales_field(
            "work_location_region",
            field_type="single_select",
            name="Work region",
            reference_domain="regions",
            reference_meta=country_filter,
        ),
        _sales_field(
            "work_location_city",
            field_type="single_select",
            name="Work city",
            reference_domain="cities",
            reference_meta=country_filter,
        ),
        _sales_field("work_location_base", field_type="text", name="Work base / depot"),
        _sales_field("job_posting_ready", field_type="single_select", name="Job posting ready"),
        _sales_field("recruitment_materials", field_type="single_select", name="Recruitment media"),
        # Sales / client branch
        _sales_field(
            "advertised_services",
            field_type="multi_select",
            name="Advertised services",
            reference_domain="services",
        ),
        _sales_field("advertised_services_other", field_type="text", name="Other advertised service"),
        _sales_field("client_geo_country", field_type="single_select", name="Client geo country", reference_domain="countries"),
        _sales_field(
            "client_geo_region",
            field_type="single_select",
            name="Client geo region",
            reference_domain="regions",
            reference_meta=client_country_filter,
        ),
        _sales_field(
            "client_geo_city",
            field_type="single_select",
            name="Client geo city",
            reference_domain="cities",
            reference_meta=client_country_filter,
        ),
        _sales_field("conversion_destination", field_type="single_select", name="Conversion destination"),
        _sales_field("has_website", field_type="single_select", name="Has website"),
        _sales_field("marketing_materials", field_type="single_select", name="Marketing media"),
        # Common contact tail
        _sales_field("contact_full_name", field_type="text", name="Contact full name"),
        _sales_field("contact_company_name", field_type="text", name="Contact company name"),
        _sales_field("contact_phone", field_type="phone_e164", name="Contact phone"),
        _sales_field("contact_email", field_type="email", name="Contact email"),
        _sales_field("additional_notes", field_type="textarea", name="Additional notes"),
    ]
    return rows


def service_sales_module_manifest() -> dict[str, Any]:
    return {
        "module": SERVICE_SALES_MODULE,
        "registry_version": "field_registry_v1",
        "canonical_fields": service_sales_targeted_advertising_fields(),
        "card_layouts": [],
    }
