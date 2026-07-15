"""Service sales Entity Profile manifests (targeted advertising questionnaire)."""

from __future__ import annotations

from typing import Any

from backend.app.entity_profile.constants import (
    ENTITY_LEAD,
    REQUIREMENT_OPTIONAL,
    REQUIREMENT_REQUIRED,
    SERVICE_SALES_MODULE,
    TARGETED_ADVERTISING_PRESENTATION_CODE,
    TARGETED_ADVERTISING_PROFILE_CODE,
)

_PREFIX = TARGETED_ADVERTISING_PROFILE_CODE
_EMPLOYEES = ("vacancies",)
_CLIENTS = ("services", "ecommerce", "real_estate", "other")


def _qc(field_code: str) -> str:
    return f"{_PREFIX}.{field_code}"


def _profile_field(
    qualified_code: str,
    *,
    sort_order: int,
    intake_level: str = REQUIREMENT_OPTIONAL,
    card_save_level: str = REQUIREMENT_OPTIONAL,
) -> dict[str, Any]:
    return {
        "qualified_code": qualified_code,
        "sort_order": sort_order,
        "intake_level": intake_level,
        "card_save_level": card_save_level,
        "transition_level": REQUIREMENT_OPTIONAL,
    }


def _employees_rule() -> dict[str, Any]:
    return {"show_if": {"source_field": _qc("need_type"), "operator": "in", "value": list(_EMPLOYEES)}}


def _clients_rule() -> dict[str, Any]:
    return {"show_if": {"source_field": _qc("need_type"), "operator": "in", "value": list(_CLIENTS)}}


def _other_profession_rule() -> dict[str, Any]:
    return {
        "show_if": {
            "source_field": _qc("recruitment_roles"),
            "operator": "in",
            "value": ["other"],
        }
    }


def _other_service_rule() -> dict[str, Any]:
    return {
        "show_if": {
            "source_field": _qc("advertised_services"),
            "operator": "in",
            "value": ["other"],
        }
    }


def _presentation_overrides() -> dict[str, dict[str, Any]]:
    employees = _employees_rule()
    clients = _clients_rule()

    return {
        _qc("need_type"): {
            "label_override": "Что вы хотите продвигать?",
            "widget_hint": "single_select",
            "intake_level": REQUIREMENT_REQUIRED,
        },
        _qc("recruitment_roles"): {
            "label_override": "Каких сотрудников вы ищете?",
            "widget_hint": "multi_select",
            "intake_level": REQUIREMENT_REQUIRED,
            "presentation_rules": employees,
        },
        _qc("recruitment_other_role"): {
            "label_override": "Укажите профессию",
            "presentation_rules": {
                "show_if_all": [employees["show_if"], _other_profession_rule()["show_if"]],
            },
        },
        _qc("recruitment_headcount"): {
            "label_override": "Сколько сотрудников требуется?",
            "intake_level": REQUIREMENT_REQUIRED,
            "presentation_rules": employees,
        },
        _qc("work_location_country"): {
            "label_override": "Страна",
            "intake_level": REQUIREMENT_REQUIRED,
            "presentation_rules": employees,
        },
        _qc("work_location_region"): {
            "label_override": "Регион",
            "intake_level": REQUIREMENT_REQUIRED,
            "presentation_rules": employees,
        },
        _qc("work_location_city"): {
            "label_override": "Город",
            "intake_level": REQUIREMENT_REQUIRED,
            "presentation_rules": employees,
        },
        _qc("work_location_base"): {
            "label_override": "База / депо (если есть)",
            "presentation_rules": employees,
        },
        _qc("job_posting_ready"): {
            "label_override": "Есть ли готовое объявление?",
            "presentation_rules": employees,
        },
        _qc("recruitment_materials"): {
            "label_override": "Есть ли фото или видео?",
            "presentation_rules": employees,
        },
        _qc("advertised_services"): {
            "label_override": "Какие услуги или товары вы хотите рекламировать?",
            "widget_hint": "multi_select",
            "intake_level": REQUIREMENT_REQUIRED,
            "presentation_rules": clients,
        },
        _qc("advertised_services_other"): {
            "label_override": "Другая услуга",
            "presentation_rules": {
                "show_if_all": [clients["show_if"], _other_service_rule()["show_if"]],
            },
        },
        _qc("client_geo_country"): {
            "label_override": "Страна",
            "intake_level": REQUIREMENT_REQUIRED,
            "presentation_rules": clients,
        },
        _qc("client_geo_region"): {
            "label_override": "Регион",
            "intake_level": REQUIREMENT_REQUIRED,
            "presentation_rules": clients,
        },
        _qc("client_geo_city"): {
            "label_override": "Город",
            "intake_level": REQUIREMENT_REQUIRED,
            "presentation_rules": clients,
        },
        _qc("conversion_destination"): {
            "label_override": "Что должен сделать клиент после рекламы?",
            "intake_level": REQUIREMENT_REQUIRED,
            "presentation_rules": clients,
        },
        _qc("has_website"): {
            "label_override": "Есть ли сайт?",
            "presentation_rules": clients,
        },
        _qc("marketing_materials"): {
            "label_override": "Есть ли фото или видео?",
            "presentation_rules": clients,
        },
        _qc("contact_full_name"): {
            "label_override": "Имя",
            "intake_level": REQUIREMENT_REQUIRED,
        },
        _qc("contact_company_name"): {
            "label_override": "Компания",
        },
        _qc("contact_phone"): {
            "label_override": "Телефон",
            "intake_level": REQUIREMENT_REQUIRED,
        },
        _qc("contact_email"): {
            "label_override": "Email",
            "intake_level": REQUIREMENT_REQUIRED,
        },
        _qc("additional_notes"): {
            "label_override": "Комментарий",
            "widget_hint": "textarea",
        },
    }


def _presentation_field_subset() -> list[str]:
    return [
        _qc("need_type"),
        _qc("recruitment_roles"),
        _qc("recruitment_other_role"),
        _qc("recruitment_headcount"),
        _qc("work_location_country"),
        _qc("work_location_region"),
        _qc("work_location_city"),
        _qc("work_location_base"),
        _qc("job_posting_ready"),
        _qc("recruitment_materials"),
        _qc("advertised_services"),
        _qc("advertised_services_other"),
        _qc("client_geo_country"),
        _qc("client_geo_region"),
        _qc("client_geo_city"),
        _qc("conversion_destination"),
        _qc("has_website"),
        _qc("marketing_materials"),
        _qc("contact_full_name"),
        _qc("contact_company_name"),
        _qc("contact_phone"),
        _qc("contact_email"),
        _qc("additional_notes"),
    ]


def service_sales_targeted_advertising_profile() -> dict[str, Any]:
    """Branching B2B questionnaire: employees vs clients vs both."""
    overrides = _presentation_overrides()
    return {
        "profile_code": TARGETED_ADVERTISING_PROFILE_CODE,
        "entity_type": ENTITY_LEAD,
        "module_owner": SERVICE_SALES_MODULE,
        "name": "Targeted Advertising Questionnaire",
        "description": "Conditional sales questionnaire with platform library-backed selects.",
        "default_layout_code": None,
        "document_pack_code": None,
        "process_profile_code": None,
        "config": {
            "market_country": "PL",
            "default_language": "ru",
            "questionnaire_kind": "targeted_advertising",
        },
        "fields": [
            _profile_field(_qc("need_type"), sort_order=10, intake_level=REQUIREMENT_REQUIRED),
            _profile_field(_qc("recruitment_roles"), sort_order=110),
            _profile_field(_qc("recruitment_other_role"), sort_order=120),
            _profile_field(_qc("recruitment_headcount"), sort_order=130),
            _profile_field(_qc("work_location_country"), sort_order=140),
            _profile_field(_qc("work_location_region"), sort_order=150),
            _profile_field(_qc("work_location_city"), sort_order=160),
            _profile_field(_qc("work_location_base"), sort_order=170),
            _profile_field(_qc("job_posting_ready"), sort_order=180),
            _profile_field(_qc("recruitment_materials"), sort_order=190),
            _profile_field(_qc("advertised_services"), sort_order=210),
            _profile_field(_qc("advertised_services_other"), sort_order=220),
            _profile_field(_qc("client_geo_country"), sort_order=230),
            _profile_field(_qc("client_geo_region"), sort_order=240),
            _profile_field(_qc("client_geo_city"), sort_order=250),
            _profile_field(_qc("conversion_destination"), sort_order=260),
            _profile_field(_qc("has_website"), sort_order=270),
            _profile_field(_qc("marketing_materials"), sort_order=280),
            _profile_field(_qc("contact_full_name"), sort_order=410, intake_level=REQUIREMENT_REQUIRED),
            _profile_field(_qc("contact_company_name"), sort_order=420),
            _profile_field(_qc("contact_phone"), sort_order=430, intake_level=REQUIREMENT_REQUIRED),
            _profile_field(_qc("contact_email"), sort_order=440, intake_level=REQUIREMENT_REQUIRED),
            _profile_field(_qc("additional_notes"), sort_order=450),
        ],
        "intake_presentations": [
            {
                "presentation_code": TARGETED_ADVERTISING_PRESENTATION_CODE,
                "field_subset": _presentation_field_subset(),
                "presentation_overrides": overrides,
            },
        ],
    }


def service_sales_module_entity_profiles() -> list[dict[str, Any]]:
    return [service_sales_targeted_advertising_profile()]
