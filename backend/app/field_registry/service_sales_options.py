"""Human-readable option sets for service_sales.targeted_advertising questionnaire fields.

Library-backed fields (countries, regions, cities, professions, services) resolve via
``intake_reference_options`` — only simple enum fields remain here.
"""

from __future__ import annotations

from typing import Any

from backend.app.entity_profile.constants import TARGETED_ADVERTISING_PROFILE_CODE
from backend.app.field_registry.intake_reference_options import attach_library_options_to_presentation_field

_PREFIX = TARGETED_ADVERTISING_PROFILE_CODE

# Fields resolved from platform libraries — skip static options.
_LIBRARY_SUFFIXES = frozenset(
    {
        "recruitment_roles",
        "work_location_country",
        "work_location_region",
        "work_location_city",
        "advertised_services",
        "client_geo_country",
        "client_geo_region",
        "client_geo_city",
    }
)


def _opt(value: str, label: str) -> dict[str, str]:
    return {"value": value, "label": label}


def _options_for_suffix(suffix: str) -> list[dict[str, str]]:
    if suffix in _LIBRARY_SUFFIXES:
        return []
    catalog: dict[str, list[dict[str, str]]] = {
        "need_type": [
            _opt("services", "Услуги"),
            _opt("vacancies", "Вакансии"),
            _opt("ecommerce", "Интернет-магазин"),
            _opt("real_estate", "Недвижимость"),
            _opt("other", "Другое"),
        ],
        "recruitment_headcount": [
            _opt("1_2", "1–2"),
            _opt("3_5", "3–5"),
            _opt("6_10", "6–10"),
            _opt("10_plus", "Более 10"),
        ],
        "job_posting_ready": [
            _opt("yes", "Да"),
            _opt("no", "Нет"),
        ],
        "recruitment_materials": [
            _opt("yes", "Да"),
            _opt("no", "Нет"),
            _opt("need_create", "Нужно создать"),
        ],
        "conversion_destination": [
            _opt("phone", "Позвонить"),
            _opt("form", "Оставить заявку"),
            _opt("whatsapp", "Написать WhatsApp"),
            _opt("telegram", "Написать Telegram"),
            _opt("buy", "Купить"),
            _opt("other", "Другое"),
        ],
        "has_website": [
            _opt("yes", "Да"),
            _opt("no", "Нет"),
        ],
        "marketing_materials": [
            _opt("yes", "Да"),
            _opt("no", "Нет"),
            _opt("need_create", "Нужно создать"),
        ],
        # Legacy values for old submissions / hidden fields
        "primary_outcome": [],
        "promotion_subject": [],
        "industry": [],
        "client_geo_scope": [],
        "application_channel": [],
        "offer_ready": [],
        "prior_ads_experience": [],
        "monthly_ad_budget": [],
        "start_timeline": [],
        "decision_maker": [],
    }
    return catalog.get(suffix, [])


def service_sales_field_options(qualified_code: str) -> list[dict[str, str]]:
    code = str(qualified_code or "").strip()
    if not code.startswith(f"{_PREFIX}."):
        return []
    suffix = code.split(".")[-1]
    return list(_options_for_suffix(suffix))


def attach_options_to_presentation_field(field_row: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a presentation runtime field with ``options`` when applicable."""
    row = attach_library_options_to_presentation_field(dict(field_row))
    qcode = str(row.get("qualified_code") or "").strip()
    field_type = str(row.get("field_type") or row.get("widget_hint") or "").lower()
    if row.get("options"):
        return row
    if "select" in field_type and qcode:
        options = service_sales_field_options(qcode)
        if options:
            row["options"] = options
    return row
