"""Entity Profile: company questionnaire for hiring warehouse / general labor."""

from __future__ import annotations

from typing import Any

from backend.app.entity_profile.constants import (
    ENTITY_LEAD,
    REQUIREMENT_OPTIONAL,
    REQUIREMENT_REQUIRED,
    SERVICE_SALES_MODULE,
    WAREHOUSE_HIRING_PRESENTATION_CODE,
    WAREHOUSE_HIRING_PROFILE_CODE,
)
from backend.app.field_registry.manifests.service_sales_warehouse_hiring import (
    WAREHOUSE_HIRING_FIELD_ROWS,
    WAREHOUSE_HIRING_PREFIX,
)

_PREFIX = WAREHOUSE_HIRING_PREFIX

REQUIRED_CODES = frozenset(
    {
        "contact_company_name",
        "workers_needed",
        "worker_roles",
        "contact_full_name",
        "contact_phone",
        "contact_email",
    }
)

# Polish operator-facing fallbacks; UI prefers public.intake.presentation.fields i18n.
LABELS_PL: dict[str, str] = {
    "contact_company_name": "Nazwa firmy",
    "work_location": "Gdzie znajduje się miejsce pracy?",
    "workers_needed": "Ilu pracowników jest potrzebnych?",
    "worker_roles": "Jakich pracowników potrzebujecie?",
    "worker_roles_other": "Jaka inna rola?",
    "first_workers_when": "Kiedy potrzebni są pierwsi pracownicy?",
    "monthly_hire_volume": "Ilu pracowników planujecie zatrudniać miesięcznie?",
    "job_tasks": "Jakie zadania wykonuje pracownik?",
    "job_tasks_other": "Jakie inne zadanie?",
    "physical_demand": "Na ile fizycznie ciężka jest praca?",
    "max_lift_weight": "Jaki maksymalny ciężar trzeba podnosić ręcznie?",
    "work_posture": "Praca wykonywana jest głównie",
    "has_productivity_norms": "Czy są normy wydajności?",
    "productivity_norm": "Jaka jest norma?",
    "kpi_system": "Czy stosowana jest systematyka KPI / akordu?",
    "workplace_temperature": "Jaka temperatura jest na stanowisku pracy?",
    "shift_length": "Jaki jest grafik pracy?",
    "shift_length_other": "Jaki inny grafik?",
    "shift_count": "Ile zmian?",
    "shift_types": "Jakie zmiany są przewidziane?",
    "workdays_per_week": "Ile dni roboczych w tygodniu?",
    "weekend_work": "Czy możliwa jest praca w weekendy?",
    "overtime": "Czy możliwe są nadgodziny?",
    "monthly_hours": "Ile godzin średnio można pracować w miesiącu?",
    "pay_system": "Jaki jest system wynagrodzenia?",
    "pay_system_other": "Jaki inny system wynagrodzenia?",
    "pay_netto_amount": "Jaka stawka netto?",
    "pay_netto_unit": "Jednostka stawki netto",
    "pay_brutto_amount": "Jaka stawka brutto?",
    "pay_brutto_unit": "Jednostka stawki brutto",
    "guaranteed_hours": "Czy jest gwarantowana liczba godzin?",
    "guaranteed_hours_amount": "Ile godzin w miesiącu jest gwarantowanych?",
    "has_bonuses": "Czy są bonusy / premie?",
    "bonus_types": "Za co są bonusy?",
    "bonus_types_other": "Jaki inny bonus?",
    "overtime_pay": "Jak wypłacane są nadgodziny?",
    "overtime_pay_other": "Jak inaczej wypłacane są nadgodziny?",
    "pay_frequency": "Jak często wypłacane jest wynagrodzenie?",
    "pay_frequency_other": "Jak inaczej wypłacane jest wynagrodzenie?",
    "advances": "Czy możliwe są zaliczki?",
    "contract_types": "Jaka umowa jest oferowana?",
    "contract_types_other": "Jaka inna umowa?",
    "legal_employer": "Kto jest oficjalnym pracodawcą?",
    "has_probation": "Czy jest okres próbny?",
    "probation_length": "Jaki jest okres próbny?",
    "medical_exam_payer": "Kto opłaca badania lekarskie?",
    "workwear": "Czy zapewniana jest odzież i obuwie robocze?",
    "experience_required": "Czy wymagane jest doświadczenie?",
    "min_experience": "Jakie minimalne doświadczenie jest wymagane?",
    "extra_qualifications": "Czy wymagane są dodatkowe kwalifikacje?",
    "extra_qualifications_other": "Jakie inne kwalifikacje?",
    "language_required": "Czy wymagana jest znajomość języka?",
    "languages": "Jaki język jest wymagany?",
    "languages_other": "Jaki inny język?",
    "language_level": "Jaki jest minimalny poziom języka?",
    "gender_considered": "Kogo rozważacie?",
    "citizenships": "Kandydatów z jakich obywatelstw rozważacie?",
    "citizenships_other": "Jakie inne obywatelstwo?",
    "required_documents": "Jakie dokumenty są niezbędne?",
    "required_documents_other": "Jaki inny dokument?",
    "stay_document_min_validity": "Jaki minimalny pozostały okres legalnego pobytu jest wymagany?",
    "housing": "Czy zapewniane jest zakwaterowanie?",
    "housing_cost": "Ile kosztuje zakwaterowanie? (PLN/miesiąc)",
    "roommates": "Ile osób mieszka w pokoju?",
    "housing_distance_km": "Jaka jest odległość od zakwaterowania do pracy? (km)",
    "transport_to_work": "Czy zapewniany jest transport do pracy?",
    "transport_cost": "Ile kosztuje transport? (PLN/miesiąc)",
    "selection_process": "Jak przebiega rekrutacja?",
    "decision_time": "W jakim czasie podejmowana jest decyzja o kandydacie?",
    "start_after_approval": "Kiedy kandydat może zacząć pracę po akceptacji?",
    "has_onboarding": "Czy jest zorganizowany onboarding / szkolenie?",
    "onboarding_duration": "Ile trwa szkolenie?",
    "hire_themselves": "Czy zatrudniacie pracowników samodzielnie?",
    "other_agencies": "Czy współpracujecie z innymi agencjami?",
    "hired_last_3_months": "Ilu pracowników zatrudniono w ostatnich 3 miesiącach?",
    "leavers_per_month": "Ilu pracowników średnio odchodzi w miesiącu?",
    "hiring_problems": "Jaki jest główny problem przy rekrutacji?",
    "hiring_problems_other": "Jaki inny problem?",
    "refusal_reasons": "Dlaczego kandydaci najczęściej odmawiają?",
    "refusal_reasons_other": "Jaka inna przyczyna odmowy?",
    "weekly_candidate_capacity": "Ilu kandydatów możecie obsługiwać w tygodniu?",
    "contact_full_name": "Osoba kontaktowa ds. rekrutacji",
    "contact_phone": "Telefon osoby kontaktowej",
    "contact_email": "E-mail osoby kontaktowej",
}

WIDGET_HINTS = {
    "text": "text",
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
        "worker_roles_other": _contains("worker_roles", "other"),
        "job_tasks_other": _contains("job_tasks", "other"),
        "productivity_norm": _contains("has_productivity_norms", "yes"),
        "shift_length_other": _contains("shift_length", "other"),
        "pay_system_other": _contains("pay_system", "other"),
        "guaranteed_hours_amount": _contains("guaranteed_hours", "yes"),
        "bonus_types": _contains("has_bonuses", "yes"),
        "bonus_types_other": _contains("bonus_types", "other"),
        "overtime_pay_other": _contains("overtime_pay", "other"),
        "pay_frequency_other": _contains("pay_frequency", "other"),
        "contract_types_other": _contains("contract_types", "other"),
        "probation_length": _contains("has_probation", "yes"),
        "min_experience": _contains("experience_required", "preferred", "required"),
        "extra_qualifications_other": _contains("extra_qualifications", "other"),
        "languages": _contains("language_required", "yes", "preferred"),
        "languages_other": _contains("languages", "other"),
        "language_level": _contains("language_required", "yes", "preferred"),
        "citizenships_other": _contains("citizenships", "other"),
        "required_documents_other": _contains("required_documents", "other"),
        "housing_cost": _contains("housing", "paid"),
        "roommates": _contains("housing", "free", "paid"),
        "housing_distance_km": _contains("housing", "free", "paid"),
        "transport_cost": _contains("transport_to_work", "paid"),
        "onboarding_duration": _contains("has_onboarding", "paid", "unpaid"),
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
    type_by_code = {code: ftype for code, ftype, _name, _section in WAREHOUSE_HIRING_FIELD_ROWS}
    out: dict[str, dict[str, Any]] = {}
    for code, _ftype, _name, _section in WAREHOUSE_HIRING_FIELD_ROWS:
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
    return [_qc(code) for code, _ftype, _name, _section in WAREHOUSE_HIRING_FIELD_ROWS]


def service_sales_warehouse_hiring_profile() -> dict[str, Any]:
    """Company (B2B) questionnaire: a firm wants the agency to hire warehouse / general labor."""
    overrides = _presentation_overrides()
    fields = [
        _profile_field(code, sort_order=(index + 1) * 10)
        for index, (code, _ftype, _name, _section) in enumerate(WAREHOUSE_HIRING_FIELD_ROWS)
    ]
    return {
        "profile_code": WAREHOUSE_HIRING_PROFILE_CODE,
        "entity_type": ENTITY_LEAD,
        "module_owner": SERVICE_SALES_MODULE,
        "name": "Company warehouse hiring questionnaire",
        "description": "Sales inquiry questionnaire for companies that want to hire warehouse workers or general laborers.",
        "default_layout_code": None,
        "document_pack_code": None,
        "process_profile_code": None,
        "config": {
            "market_country": "PL",
            "default_language": "pl",
            "questionnaire_kind": "warehouse_hiring",
        },
        "fields": fields,
        "intake_presentations": [
            {
                "presentation_code": WAREHOUSE_HIRING_PRESENTATION_CODE,
                "field_subset": _presentation_field_subset(),
                "presentation_overrides": overrides,
            },
        ],
    }
