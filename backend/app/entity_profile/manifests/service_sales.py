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
from backend.app.entity_profile.manifests.service_sales_driver_hiring import (
    service_sales_driver_hiring_profile,
)
from backend.app.entity_profile.manifests.service_sales_warehouse_hiring import (
    service_sales_warehouse_hiring_profile,
)

_PREFIX = TARGETED_ADVERTISING_PROFILE_CODE
_RECRUITMENT_NEED = "employee_recruitment"
_SALES_NEEDS = ("client_acquisition", "product_sales", "service_promotion")


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


def _need_type_rule(*values: str) -> dict[str, Any]:
    if len(values) == 1:
        return {"show_if": {"source_field": _qc("need_type"), "operator": "eq", "value": values[0]}}
    return {"show_if": {"source_field": _qc("need_type"), "operator": "in", "value": list(values)}}


def _presentation_overrides() -> dict[str, dict[str, Any]]:
    """Polish labels + conditional presentation rules (recruitment vs sales branches)."""
    recruitment = _need_type_rule(_RECRUITMENT_NEED)
    sales = _need_type_rule(*_SALES_NEEDS)
    geo_detail = {
        "show_if": {
            "source_field": _qc("client_geo_scope"),
            "operator": "in",
            "value": ["single_city", "selected_region"],
        }
    }

    return {
        _qc("need_type"): {
            "label_override": "Czego dotyczy Państwa potrzeba?",
            "widget_hint": "single_select",
        },
        _qc("primary_outcome"): {
            "label_override": "Jaki wynik jest dla Państwa najważniejszy?",
            "widget_hint": "single_select",
        },
        _qc("recruitment_roles"): {
            "label_override": "Jakich pracowników chcą Państwo pozyskiwać?",
            "widget_hint": "multi_select",
            "presentation_rules": recruitment,
        },
        _qc("recruitment_other_role"): {
            "label_override": "Jakie stanowisko?",
            "presentation_rules": recruitment,
        },
        _qc("recruitment_headcount"): {
            "label_override": "Ilu pracowników potrzebują Państwo obecnie?",
            "presentation_rules": recruitment,
        },
        _qc("work_location_country"): {
            "label_override": "Gdzie znajduje się miejsce pracy?",
            "presentation_rules": recruitment,
        },
        _qc("work_location_city"): {
            "label_override": "Proszę podać miasto lub bazę",
            "presentation_rules": recruitment,
        },
        _qc("application_channel"): {
            "label_override": "Jak kandydaci powinni się zgłaszać?",
            "presentation_rules": recruitment,
        },
        _qc("job_posting_ready"): {
            "label_override": "Czy mają Państwo gotowe ogłoszenie o pracę?",
            "presentation_rules": recruitment,
        },
        _qc("recruitment_materials"): {
            "label_override": "Czy mają Państwo materiały do reklamy rekrutacyjnej?",
            "widget_hint": "multi_select",
            "presentation_rules": recruitment,
        },
        _qc("promotion_subject"): {
            "label_override": "Co chcą Państwo promować?",
            "presentation_rules": sales,
        },
        _qc("industry"): {
            "label_override": "W jakiej branży działa firma?",
            "presentation_rules": sales,
        },
        _qc("target_audience_description"): {
            "label_override": "Kogo konkretnie chcą Państwo przyciągnąć?",
            "widget_hint": "textarea",
            "presentation_rules": sales,
        },
        _qc("qualified_lead_definition"): {
            "label_override": "Jaki kontakt lub lead uznają Państwo za odpowiedni?",
            "widget_hint": "textarea",
            "presentation_rules": sales,
        },
        _qc("client_geo_scope"): {
            "label_override": "Gdzie chcą Państwo pozyskiwać klientów?",
            "presentation_rules": sales,
        },
        _qc("client_geo_detail"): {
            "label_override": "Proszę podać miasto lub region",
            "presentation_rules": {**sales, **geo_detail},
        },
        _qc("conversion_destination"): {
            "label_override": "Dokąd mają trafiać klienci z reklamy?",
            "presentation_rules": sales,
        },
        _qc("offer_ready"): {
            "label_override": "Czy mają Państwo gotową ofertę?",
            "presentation_rules": sales,
        },
        _qc("marketing_materials"): {
            "label_override": "Czy mają Państwo materiały reklamowe?",
            "widget_hint": "multi_select",
            "presentation_rules": sales,
        },
        _qc("prior_ads_experience"): {
            "label_override": "Czy wcześniej korzystali Państwo z reklam na Facebooku lub Instagramie?",
        },
        _qc("monthly_ad_budget"): {
            "label_override": "Jaki miesięczny budżet chcą Państwo przeznaczyć bezpośrednio na reklamę?",
        },
        _qc("start_timeline"): {
            "label_override": "Kiedy chcą Państwo rozpocząć działania?",
        },
        _qc("decision_maker"): {
            "label_override": "Kto podejmuje decyzję o współpracy?",
        },
        _qc("contact_full_name"): {
            "label_override": "Imię i nazwisko",
            "intake_level": REQUIREMENT_REQUIRED,
        },
        _qc("contact_company_name"): {
            "label_override": "Nazwa firmy",
            "intake_level": REQUIREMENT_REQUIRED,
        },
        _qc("contact_phone"): {
            "label_override": "Numer telefonu",
            "intake_level": REQUIREMENT_REQUIRED,
        },
        _qc("contact_email"): {
            "label_override": "Adres e-mail",
            "intake_level": REQUIREMENT_REQUIRED,
        },
        _qc("contact_website"): {
            "label_override": "Strona internetowa lub profil firmy",
        },
        _qc("additional_notes"): {
            "label_override": "Czy jest coś ważnego, co powinniśmy wiedzieć?",
            "widget_hint": "textarea",
        },
    }


def _presentation_field_subset() -> list[str]:
    return [
        _qc("need_type"),
        _qc("primary_outcome"),
        _qc("recruitment_roles"),
        _qc("recruitment_other_role"),
        _qc("recruitment_headcount"),
        _qc("work_location_country"),
        _qc("work_location_city"),
        _qc("application_channel"),
        _qc("job_posting_ready"),
        _qc("recruitment_materials"),
        _qc("promotion_subject"),
        _qc("industry"),
        _qc("target_audience_description"),
        _qc("qualified_lead_definition"),
        _qc("client_geo_scope"),
        _qc("client_geo_detail"),
        _qc("conversion_destination"),
        _qc("offer_ready"),
        _qc("marketing_materials"),
        _qc("prior_ads_experience"),
        _qc("monthly_ad_budget"),
        _qc("start_timeline"),
        _qc("decision_maker"),
        _qc("contact_full_name"),
        _qc("contact_company_name"),
        _qc("contact_phone"),
        _qc("contact_email"),
        _qc("contact_website"),
        _qc("additional_notes"),
    ]


def service_sales_targeted_advertising_profile() -> dict[str, Any]:
    """Targeted advertising sales questionnaire bound to existing Meta/client leads."""
    overrides = _presentation_overrides()
    return {
        "profile_code": TARGETED_ADVERTISING_PROFILE_CODE,
        "entity_type": ENTITY_LEAD,
        "module_owner": SERVICE_SALES_MODULE,
        "name": "Targeted Advertising Questionnaire",
        "description": "Conditional sales questionnaire for targeted advertising service inquiries (PL).",
        "default_layout_code": None,
        "document_pack_code": None,
        "process_profile_code": None,
        "config": {
            "market_country": "PL",
            "default_language": "pl",
            "questionnaire_kind": "targeted_advertising",
        },
        "fields": [
            _profile_field(_qc("need_type"), sort_order=10, intake_level=REQUIREMENT_REQUIRED),
            _profile_field(_qc("primary_outcome"), sort_order=20, intake_level=REQUIREMENT_REQUIRED),
            _profile_field(_qc("recruitment_roles"), sort_order=110),
            _profile_field(_qc("recruitment_other_role"), sort_order=120),
            _profile_field(_qc("recruitment_headcount"), sort_order=130),
            _profile_field(_qc("work_location_country"), sort_order=140),
            _profile_field(_qc("work_location_city"), sort_order=150),
            _profile_field(_qc("application_channel"), sort_order=160),
            _profile_field(_qc("job_posting_ready"), sort_order=170),
            _profile_field(_qc("recruitment_materials"), sort_order=180),
            _profile_field(_qc("promotion_subject"), sort_order=210),
            _profile_field(_qc("industry"), sort_order=220),
            _profile_field(_qc("target_audience_description"), sort_order=225),
            _profile_field(_qc("qualified_lead_definition"), sort_order=228),
            _profile_field(_qc("client_geo_scope"), sort_order=230),
            _profile_field(_qc("client_geo_detail"), sort_order=240),
            _profile_field(_qc("conversion_destination"), sort_order=250),
            _profile_field(_qc("offer_ready"), sort_order=260),
            _profile_field(_qc("marketing_materials"), sort_order=270),
            _profile_field(_qc("prior_ads_experience"), sort_order=310),
            _profile_field(_qc("monthly_ad_budget"), sort_order=320),
            _profile_field(_qc("start_timeline"), sort_order=330),
            _profile_field(_qc("decision_maker"), sort_order=340),
            _profile_field(_qc("contact_full_name"), sort_order=410, intake_level=REQUIREMENT_REQUIRED),
            _profile_field(_qc("contact_company_name"), sort_order=420, intake_level=REQUIREMENT_REQUIRED),
            _profile_field(_qc("contact_phone"), sort_order=430, intake_level=REQUIREMENT_REQUIRED),
            _profile_field(_qc("contact_email"), sort_order=440, intake_level=REQUIREMENT_REQUIRED),
            _profile_field(_qc("contact_website"), sort_order=450),
            _profile_field(_qc("additional_notes"), sort_order=460),
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
    return [
        service_sales_targeted_advertising_profile(),
        service_sales_driver_hiring_profile(),
        service_sales_warehouse_hiring_profile(),
    ]
