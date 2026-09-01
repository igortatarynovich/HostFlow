"""Canonical fields for the company warehouse / general-labor sales questionnaire."""

from __future__ import annotations

from typing import Any

from backend.app.field_registry.constants import ENTITY_LEAD, SERVICE_SALES_MODULE

WAREHOUSE_HIRING_PREFIX = "service_sales.warehouse_hiring"

# code, field_type, English name, section
WAREHOUSE_HIRING_FIELD_ROWS: list[tuple[str, str, str, str]] = [
    ("contact_company_name", "text", "Company name", "company_need"),
    ("work_location", "text", "Work location", "company_need"),
    ("workers_needed", "integer", "Workers needed", "company_need"),
    ("worker_roles", "multi_select", "Workers needed by role", "company_need"),
    ("worker_roles_other", "text", "Other worker role", "company_need"),
    ("first_workers_when", "single_select", "When first workers are needed", "company_need"),
    ("monthly_hire_volume", "single_select", "Monthly hire volume", "company_need"),
    ("job_tasks", "multi_select", "Job tasks", "work_nature"),
    ("job_tasks_other", "text", "Other job task", "work_nature"),
    ("physical_demand", "single_select", "Physical demand", "work_nature"),
    ("max_lift_weight", "single_select", "Maximum manual lift weight", "work_nature"),
    ("work_posture", "single_select", "How work is performed", "work_nature"),
    ("has_productivity_norms", "single_select", "Productivity norms", "work_nature"),
    ("productivity_norm", "text", "Productivity norm details", "work_nature"),
    ("kpi_system", "single_select", "KPI or piece-rate system", "work_nature"),
    ("workplace_temperature", "single_select", "Workplace temperature", "work_nature"),
    ("shift_length", "multi_select", "Shift length", "schedule"),
    ("shift_length_other", "text", "Other shift length", "schedule"),
    ("shift_count", "single_select", "Number of shifts", "schedule"),
    ("shift_types", "multi_select", "Shift types", "schedule"),
    ("workdays_per_week", "single_select", "Workdays per week", "schedule"),
    ("weekend_work", "single_select", "Weekend work", "schedule"),
    ("overtime", "single_select", "Overtime hours", "schedule"),
    ("monthly_hours", "integer", "Average monthly hours", "schedule"),
    ("pay_system", "single_select", "Pay system", "pay"),
    ("pay_system_other", "text", "Other pay system", "pay"),
    ("pay_netto_amount", "integer", "Netto rate amount", "pay"),
    ("pay_netto_unit", "single_select", "Netto rate unit", "pay"),
    ("pay_brutto_amount", "integer", "Brutto rate amount", "pay"),
    ("pay_brutto_unit", "single_select", "Brutto rate unit", "pay"),
    ("guaranteed_hours", "single_select", "Guaranteed hours", "pay"),
    ("guaranteed_hours_amount", "integer", "Guaranteed hours per month", "pay"),
    ("has_bonuses", "single_select", "Bonuses or premiums", "pay"),
    ("bonus_types", "multi_select", "Bonus types", "pay"),
    ("bonus_types_other", "text", "Other bonus type", "pay"),
    ("overtime_pay", "single_select", "Overtime pay", "pay"),
    ("overtime_pay_other", "text", "Other overtime pay", "pay"),
    ("pay_frequency", "single_select", "Pay frequency", "pay"),
    ("pay_frequency_other", "text", "Other pay frequency", "pay"),
    ("advances", "single_select", "Advances", "pay"),
    ("contract_types", "multi_select", "Contract types", "employment"),
    ("contract_types_other", "text", "Other contract", "employment"),
    ("legal_employer", "text", "Official employer", "employment"),
    ("has_probation", "single_select", "Probation period", "employment"),
    ("probation_length", "text", "Probation length", "employment"),
    ("medical_exam_payer", "single_select", "Who pays the medical exam", "employment"),
    ("workwear", "single_select", "Workwear and shoes provided", "employment"),
    ("experience_required", "single_select", "Experience required", "requirements"),
    ("min_experience", "single_select", "Minimum experience", "requirements"),
    ("extra_qualifications", "multi_select", "Extra qualifications", "requirements"),
    ("extra_qualifications_other", "text", "Other qualification", "requirements"),
    ("language_required", "single_select", "Language required", "requirements"),
    ("languages", "multi_select", "Languages required", "requirements"),
    ("languages_other", "text", "Other language", "requirements"),
    ("language_level", "single_select", "Minimum language level", "requirements"),
    ("gender_considered", "multi_select", "Who is considered", "requirements"),
    ("citizenships", "multi_select", "Citizenships considered", "requirements"),
    ("citizenships_other", "text", "Other citizenship", "requirements"),
    ("required_documents", "multi_select", "Required documents", "requirements"),
    ("required_documents_other", "text", "Other required document", "requirements"),
    ("stay_document_min_validity", "single_select", "Minimum stay document validity", "requirements"),
    ("housing", "single_select", "Housing provided", "housing"),
    ("housing_cost", "integer", "Housing cost", "housing"),
    ("roommates", "single_select", "People per room", "housing"),
    ("housing_distance_km", "integer", "Housing distance to work", "housing"),
    ("transport_to_work", "single_select", "Transport to work", "housing"),
    ("transport_cost", "integer", "Transport cost", "housing"),
    ("selection_process", "multi_select", "Selection process", "hiring"),
    ("decision_time", "single_select", "Decision time", "hiring"),
    ("start_after_approval", "single_select", "Start after approval", "hiring"),
    ("has_onboarding", "single_select", "Onboarding or training", "hiring"),
    ("onboarding_duration", "single_select", "Training duration", "hiring"),
    ("hire_themselves", "single_select", "Hires workers independently", "volume"),
    ("other_agencies", "single_select", "Works with other agencies", "volume"),
    ("hired_last_3_months", "integer", "Workers hired last 3 months", "volume"),
    ("leavers_per_month", "integer", "Workers leaving per month", "volume"),
    ("hiring_problems", "multi_select", "Main hiring problems", "volume"),
    ("hiring_problems_other", "text", "Other hiring problem", "volume"),
    ("refusal_reasons", "multi_select", "Why candidates refuse", "volume"),
    ("refusal_reasons_other", "text", "Other refusal reason", "volume"),
    ("weekly_candidate_capacity", "single_select", "Weekly candidate capacity", "volume"),
    ("contact_full_name", "text", "Agency contact name", "contact"),
    ("contact_phone", "phone_e164", "Agency contact phone", "contact"),
    ("contact_email", "email", "Agency contact email", "contact"),
]


def _warehouse_hiring_field(field_code: str, *, field_type: str, name: str, section: str) -> dict[str, Any]:
    qualified = f"{WAREHOUSE_HIRING_PREFIX}.{field_code}"
    pii = "business" if field_code.startswith("contact_") else None
    return {
        "qualified_code": qualified,
        "code": field_code.replace(".", "_"),
        "entity_type": ENTITY_LEAD,
        "field_type": field_type,
        "name": name,
        "label_key": f"fields.service_sales_warehouse_hiring_{field_code}",
        "ownership": SERVICE_SALES_MODULE,
        "pii_class": pii,
        "reference_domain": None,
        "storage": {"kind": "json_path", "path": f"sales_questionnaire.{field_code}"},
        "legacy_aliases": [field_code],
        "default_section": section,
    }


def service_sales_warehouse_hiring_fields() -> list[dict[str, Any]]:
    return [
        _warehouse_hiring_field(code, field_type=ftype, name=name, section=section)
        for code, ftype, name, section in WAREHOUSE_HIRING_FIELD_ROWS
    ]
