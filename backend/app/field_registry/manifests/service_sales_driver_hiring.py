"""Canonical fields for the company driver-hiring sales questionnaire."""

from __future__ import annotations

from typing import Any

from backend.app.field_registry.constants import ENTITY_LEAD, SERVICE_SALES_MODULE

DRIVER_HIRING_PREFIX = "service_sales.driver_hiring"

# code, field_type, English name, section
DRIVER_HIRING_FIELD_ROWS: list[tuple[str, str, str, str]] = [
    ("contact_company_name", "text", "Company name", "company_need"),
    ("base_location", "text", "Base location", "company_need"),
    ("drivers_needed", "integer", "Drivers needed", "company_need"),
    ("driver_categories", "multi_select", "Driver categories", "company_need"),
    ("driver_categories_other", "text", "Other driver category", "company_need"),
    ("first_drivers_when", "single_select", "When first drivers are needed", "company_need"),
    ("monthly_hire_plan", "single_select", "Monthly hire plan", "company_need"),
    ("transport_scope", "multi_select", "Transport type", "work_routes"),
    ("transport_scope_other", "text", "Other transport type", "work_routes"),
    ("route_countries", "multi_select", "Route countries", "work_routes"),
    ("route_countries_other", "text", "Other route countries", "work_routes"),
    ("cargo_types", "multi_select", "Cargo types", "work_routes"),
    ("cargo_types_other", "text", "Other cargo type", "work_routes"),
    ("loading_unloading", "single_select", "Loading and unloading", "work_routes"),
    ("avg_monthly_km", "integer", "Average monthly mileage", "work_routes"),
    ("vehicle_models", "text", "Vehicles used", "fleet"),
    ("trailers", "multi_select", "Trailers used", "fleet"),
    ("trailers_other", "text", "Other trailer", "fleet"),
    ("dedicated_vehicle", "single_select", "Vehicle assigned to driver", "fleet"),
    ("work_systems", "multi_select", "Work systems", "work_system"),
    ("work_systems_other", "text", "Other work system", "work_system"),
    ("individual_schedule", "single_select", "Individual schedule", "work_system"),
    ("work_start", "single_select", "Where driver starts work", "work_system"),
    ("work_start_other", "text", "Other work start", "work_system"),
    ("travel_to_base_paid", "single_select", "Travel to base paid", "work_system"),
    ("pay_system", "multi_select", "Pay system", "pay"),
    ("pay_system_other", "text", "Other pay system", "pay"),
    ("pay_netto_amount", "integer", "Netto pay amount", "pay"),
    ("pay_netto_currency", "single_select", "Netto pay currency", "pay"),
    ("day_rate_amount", "integer", "Day rate amount", "pay"),
    ("day_rate_currency", "single_select", "Day rate currency", "pay"),
    ("guaranteed_min_income", "single_select", "Guaranteed minimum income", "pay"),
    ("guaranteed_min_amount", "integer", "Guaranteed minimum amount", "pay"),
    ("extra_bonuses", "single_select", "Additional bonuses", "pay"),
    ("extra_bonuses_detail", "text", "Bonus details", "pay"),
    ("pay_frequency", "single_select", "Pay frequency", "pay"),
    ("pay_frequency_other", "text", "Other pay frequency", "pay"),
    ("advances", "single_select", "Advances", "pay"),
    ("contract_types", "multi_select", "Contract types", "employment"),
    ("contract_types_other", "text", "Other contract", "employment"),
    ("medical_psychotest_payer", "single_select", "Who pays medical and psychotests", "employment"),
    ("driver_certificate", "single_select", "Driver certificate issued", "employment"),
    ("legalization_help", "multi_select", "Legalization help", "employment"),
    ("legalization_help_other", "text", "Other legalization help", "employment"),
    ("min_experience", "single_select", "Minimum experience", "requirements"),
    ("europe_experience", "single_select", "Europe experience required", "requirements"),
    ("languages", "multi_select", "Languages required", "requirements"),
    ("languages_other", "text", "Other language", "requirements"),
    ("language_level", "single_select", "Minimum language level", "requirements"),
    ("citizenships", "multi_select", "Citizenships considered", "requirements"),
    ("citizenships_other", "text", "Other citizenship", "requirements"),
    ("required_documents", "multi_select", "Required candidate documents", "requirements"),
    ("required_documents_other", "text", "Other required document", "requirements"),
    ("stay_document_min_validity", "single_select", "Minimum stay document validity", "requirements"),
    ("housing", "single_select", "Housing provided", "housing"),
    ("housing_cost", "integer", "Housing cost", "housing"),
    ("housing_between_trips", "single_select", "Housing between trips", "housing"),
    ("personal_car_parking", "single_select", "Parking for personal car", "housing"),
    ("selection_process", "multi_select", "Selection process", "hiring"),
    ("selection_process_other", "text", "Other selection step", "hiring"),
    ("hiring_decision_maker", "text", "Who decides hiring", "hiring"),
    ("feedback_time", "single_select", "Feedback time", "hiring"),
    ("start_after_approval", "single_select", "Start after approval", "hiring"),
    ("hire_themselves", "single_select", "Hires drivers independently", "volume"),
    ("other_agencies", "single_select", "Works with other agencies", "volume"),
    ("hired_last_3_months", "integer", "Drivers hired last 3 months", "volume"),
    ("leavers_per_month", "integer", "Drivers leaving per month", "volume"),
    ("hiring_problems", "multi_select", "Main hiring problems", "volume"),
    ("hiring_problems_other", "text", "Other hiring problem", "volume"),
    ("refusal_reasons", "multi_select", "Why candidates refuse", "volume"),
    ("refusal_reasons_other", "text", "Other refusal reason", "volume"),
    ("weekly_candidate_capacity", "single_select", "Weekly candidate capacity", "volume"),
    ("contact_full_name", "text", "Agency contact name", "contact"),
    ("contact_phone", "phone_e164", "Agency contact phone", "contact"),
    ("contact_email", "email", "Agency contact email", "contact"),
]


def _driver_hiring_field(field_code: str, *, field_type: str, name: str, section: str) -> dict[str, Any]:
    qualified = f"{DRIVER_HIRING_PREFIX}.{field_code}"
    pii = "business" if field_code.startswith("contact_") else None
    return {
        "qualified_code": qualified,
        "code": field_code.replace(".", "_"),
        "entity_type": ENTITY_LEAD,
        "field_type": field_type,
        "name": name,
        "label_key": f"fields.service_sales_driver_hiring_{field_code}",
        "ownership": SERVICE_SALES_MODULE,
        "pii_class": pii,
        "reference_domain": None,
        "storage": {"kind": "json_path", "path": f"sales_questionnaire.{field_code}"},
        "legacy_aliases": [field_code],
        "default_section": section,
    }


def service_sales_driver_hiring_fields() -> list[dict[str, Any]]:
    return [
        _driver_hiring_field(code, field_type=ftype, name=name, section=section)
        for code, ftype, name, section in DRIVER_HIRING_FIELD_ROWS
    ]
