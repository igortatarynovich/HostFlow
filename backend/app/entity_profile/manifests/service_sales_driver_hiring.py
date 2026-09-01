"""Entity Profile: company questionnaire for hiring drivers (Sales inquiry)."""

from __future__ import annotations

from typing import Any

from backend.app.entity_profile.constants import (
    DRIVER_HIRING_PRESENTATION_CODE,
    DRIVER_HIRING_PROFILE_CODE,
    ENTITY_LEAD,
    REQUIREMENT_OPTIONAL,
    REQUIREMENT_REQUIRED,
    SERVICE_SALES_MODULE,
)
from backend.app.field_registry.manifests.service_sales_driver_hiring import (
    DRIVER_HIRING_FIELD_ROWS,
    DRIVER_HIRING_PREFIX,
)

_PREFIX = DRIVER_HIRING_PREFIX

REQUIRED_CODES = frozenset(
    {
        "contact_company_name",
        "drivers_needed",
        "driver_categories",
        "contact_full_name",
        "contact_phone",
        "contact_email",
    }
)

# Polish operator-facing fallbacks; UI prefers public.intake.presentation.fields i18n.
LABELS_PL: dict[str, str] = {
    "contact_company_name": "Nazwa firmy",
    "base_location": "Gdzie znajduje się baza?",
    "drivers_needed": "Ilu kierowców jest potrzebnych?",
    "driver_categories": "Jakie kategorie kierowców są potrzebne?",
    "driver_categories_other": "Jaka inna kategoria?",
    "first_drivers_when": "Kiedy potrzebni są pierwsi kierowcy?",
    "monthly_hire_plan": "Ilu kierowców planujecie zatrudniać miesięcznie?",
    "transport_scope": "Jaki typ przewozów?",
    "transport_scope_other": "Jaki inny typ przewozów?",
    "route_countries": "Po jakich krajach jeżdżą kierowcy?",
    "route_countries_other": "Jakie inne kraje?",
    "cargo_types": "Jaki typ przewozów / ładunków?",
    "cargo_types_other": "Jaki inny typ ładunku?",
    "loading_unloading": "Czy kierowca wykonuje załadunek / rozładunek?",
    "avg_monthly_km": "Jaki średni przebieg samochodu w miesiącu? (km)",
    "vehicle_models": "Jakie samochody są używane?",
    "trailers": "Jakie naczepy są używane?",
    "trailers_other": "Jaka inna naczepa?",
    "dedicated_vehicle": "Czy samochód jest przypisany do kierowcy?",
    "work_systems": "Jakie systemy pracy są dostępne?",
    "work_systems_other": "Jaki inny system pracy?",
    "individual_schedule": "Czy możliwy jest indywidualny grafik?",
    "work_start": "Skąd kierowca zaczyna pracę?",
    "work_start_other": "Skąd jeszcze kierowca zaczyna pracę?",
    "travel_to_base_paid": "Czy droga kierowcy do bazy jest płatna?",
    "pay_system": "Jaki system wynagrodzenia?",
    "pay_system_other": "Jaki inny system wynagrodzenia?",
    "pay_netto_amount": "Ile kierowca otrzymuje netto?",
    "pay_netto_currency": "Waluta wynagrodzenia netto",
    "day_rate_amount": "Jaka stawka netto za dzień?",
    "day_rate_currency": "Waluta stawki dziennej",
    "guaranteed_min_income": "Czy jest gwarantowany minimalny dochód?",
    "guaranteed_min_amount": "Jaka jest gwarantowana kwota?",
    "extra_bonuses": "Czy są dodatkowe premie?",
    "extra_bonuses_detail": "Za co i ile?",
    "pay_frequency": "Jak często wypłacane jest wynagrodzenie?",
    "pay_frequency_other": "Jak inaczej wypłacane jest wynagrodzenie?",
    "advances": "Czy możliwe są zaliczki?",
    "contract_types": "Jaka umowa jest proponowana?",
    "contract_types_other": "Jaka inna umowa?",
    "medical_psychotest_payer": "Kto płaci za badania i psychotesty?",
    "driver_certificate": "Czy wystawiacie świadectwo kierowcy?",
    "legalization_help": "Czy pomagacie w legalizacji / dokumentach?",
    "legalization_help_other": "Jaka inna pomoc w dokumentach?",
    "min_experience": "Jaki minimalny staż jest wymagany?",
    "europe_experience": "Czy wymagane jest doświadczenie w Europie?",
    "languages": "Jaki poziom języka jest wymagany?",
    "languages_other": "Jaki inny język?",
    "language_level": "Jaki minimalny poziom języka?",
    "citizenships": "Obywatelstwa, które rozważacie",
    "citizenships_other": "Jakie inne obywatelstwo?",
    "required_documents": "Jakie dokumenty musi mieć kandydat?",
    "required_documents_other": "Jaki inny dokument?",
    "stay_document_min_validity": "Jaki minimalny pozostały okres ważności dokumentów pobytowych?",
    "housing": "Czy zapewniacie zakwaterowanie?",
    "housing_cost": "Koszt zakwaterowania (PLN / miesiąc)",
    "housing_between_trips": "Czy można korzystać z mieszkania między trasami?",
    "personal_car_parking": "Czy jest parking dla prywatnego samochodu?",
    "selection_process": "Jak przebiega rekrutacja kandydata?",
    "selection_process_other": "Jaki inny etap rekrutacji?",
    "hiring_decision_maker": "Kto podejmuje decyzję o zatrudnieniu?",
    "feedback_time": "W jakim czasie dajecie informację zwrotną?",
    "start_after_approval": "Po jakim czasie od akceptacji kandydat może zacząć pracę?",
    "hire_themselves": "Czy zatrudniacie kierowców samodzielnie?",
    "other_agencies": "Czy współpracujecie teraz z innymi agencjami?",
    "hired_last_3_months": "Ilu kierowców zatrudniliście w ostatnich 3 miesiącach?",
    "leavers_per_month": "Ilu kierowców średnio odchodzi w miesiącu?",
    "hiring_problems": "Co jest teraz głównym problemem przy rekrutacji?",
    "hiring_problems_other": "Jaki inny problem?",
    "refusal_reasons": "Dlaczego kandydaci najczęściej odmawiają?",
    "refusal_reasons_other": "Jaki inny powód odmowy?",
    "weekly_candidate_capacity": "Ilu nowych kandydatów jesteście w stanie obsłużyć w tygodniu?",
    "contact_full_name": "Imię i nazwisko osoby kontaktowej",
    "contact_phone": "Telefon osoby kontaktowej",
    "contact_email": "E-mail osoby kontaktowej",
}

WIDGET_HINTS: dict[str, str] = {
    "single_select": "single_select",
    "multi_select": "multi_select",
    "integer": "number",
    "textarea": "textarea",
    "phone_e164": "phone",
    "email": "email",
}


def _qc(field_code: str) -> str:
    return f"{_PREFIX}.{field_code}"


def _contains(source: str, *values: str) -> dict[str, Any]:
    expected: Any = list(values) if len(values) > 1 else values[0]
    if isinstance(expected, list):
        return {"show_if": {"source_field": _qc(source), "operator": "in", "value": expected}}
    return {"show_if": {"source_field": _qc(source), "operator": "eq", "value": expected}}


def _presentation_rules() -> dict[str, dict[str, Any]]:
    return {
        "driver_categories_other": _contains("driver_categories", "other"),
        "transport_scope_other": _contains("transport_scope", "other"),
        "route_countries_other": _contains("route_countries", "other"),
        "cargo_types_other": _contains("cargo_types", "other"),
        "trailers_other": _contains("trailers", "other"),
        "work_systems_other": _contains("work_systems", "other"),
        "work_start_other": _contains("work_start", "other"),
        "pay_system_other": _contains("pay_system", "other"),
        "day_rate_amount": _contains("pay_system", "per_day"),
        "day_rate_currency": _contains("pay_system", "per_day"),
        "guaranteed_min_amount": _contains("guaranteed_min_income", "yes"),
        "extra_bonuses_detail": _contains("extra_bonuses", "yes"),
        "pay_frequency_other": _contains("pay_frequency", "other"),
        "contract_types_other": _contains("contract_types", "other"),
        "legalization_help_other": _contains("legalization_help", "other"),
        "languages_other": _contains("languages", "other"),
        "citizenships_other": _contains("citizenships", "other"),
        "required_documents_other": _contains("required_documents", "other"),
        "housing_cost": _contains("housing", "paid"),
        "selection_process_other": _contains("selection_process", "other"),
        "hiring_problems_other": _contains("hiring_problems", "other"),
        "refusal_reasons_other": _contains("refusal_reasons", "other"),
    }


def _profile_field(field_code: str, *, sort_order: int) -> dict[str, Any]:
    level = REQUIREMENT_REQUIRED if field_code in REQUIRED_CODES else REQUIREMENT_OPTIONAL
    return {
        "qualified_code": _qc(field_code),
        "sort_order": sort_order,
        "intake_level": level,
        "card_save_level": level,
        "transition_level": REQUIREMENT_OPTIONAL,
    }


def _presentation_overrides() -> dict[str, dict[str, Any]]:
    rules = _presentation_rules()
    type_by_code = {code: ftype for code, ftype, _name, _section in DRIVER_HIRING_FIELD_ROWS}
    out: dict[str, dict[str, Any]] = {}
    for code, _ftype, _name, _section in DRIVER_HIRING_FIELD_ROWS:
        entry: dict[str, Any] = {
            "label_override": LABELS_PL[code],
        }
        hint = WIDGET_HINTS.get(type_by_code[code])
        if hint:
            entry["widget_hint"] = hint
        if code in REQUIRED_CODES:
            entry["intake_level"] = REQUIREMENT_REQUIRED
        if code in rules:
            entry["presentation_rules"] = rules[code]
        out[_qc(code)] = entry
    return out


def _presentation_field_subset() -> list[str]:
    return [_qc(code) for code, _ftype, _name, _section in DRIVER_HIRING_FIELD_ROWS]


def service_sales_driver_hiring_profile() -> dict[str, Any]:
    """Company (B2B) questionnaire: a firm wants the agency to hire drivers."""
    overrides = _presentation_overrides()
    fields = [
        _profile_field(code, sort_order=(index + 1) * 10)
        for index, (code, _ftype, _name, _section) in enumerate(DRIVER_HIRING_FIELD_ROWS)
    ]
    return {
        "profile_code": DRIVER_HIRING_PROFILE_CODE,
        "entity_type": ENTITY_LEAD,
        "module_owner": SERVICE_SALES_MODULE,
        "name": "Company driver hiring questionnaire",
        "description": "Sales inquiry questionnaire for companies that want to hire drivers.",
        "default_layout_code": None,
        "document_pack_code": None,
        "process_profile_code": None,
        "config": {
            "market_country": "PL",
            "default_language": "pl",
            "questionnaire_kind": "driver_hiring",
        },
        "fields": fields,
        "intake_presentations": [
            {
                "presentation_code": DRIVER_HIRING_PRESENTATION_CODE,
                "field_subset": _presentation_field_subset(),
                "presentation_overrides": overrides,
            },
        ],
    }
