"""Curated public intake field sets per launch-search role (M1 money path)."""

from __future__ import annotations

from typing import Any

from backend.app.entity_profile.constants import REQUIREMENT_OPTIONAL, REQUIREMENT_REQUIRED

# widget_hint values consumed by PublicIntakePresentationForm
WIDGET_TEXT = "text"
WIDGET_EMAIL = "email"
WIDGET_PHONE = "phone"
WIDGET_DATE = "date"
WIDGET_NUMBER = "number"
WIDGET_SELECT = "select"
WIDGET_MULTISELECT = "multiselect"
WIDGET_YES_NO = "yes_no"


def _spec(
    qualified_code: str,
    *,
    sort_order: int,
    intake_level: str = REQUIREMENT_OPTIONAL,
    widget_hint: str = WIDGET_TEXT,
    card_save_level: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "qualified_code": qualified_code,
        "sort_order": sort_order,
        "intake_level": intake_level,
        "card_save_level": card_save_level or intake_level,
        "transition_level": REQUIREMENT_OPTIONAL,
        "widget_hint": widget_hint,
    }
    return row


def _presentation_overrides(specs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in specs:
        code = str(row["qualified_code"])
        override: dict[str, Any] = {}
        if row.get("widget_hint"):
            override["widget_hint"] = row["widget_hint"]
        level = str(row.get("intake_level") or "").strip()
        if level in ("required", "optional", "hidden"):
            override["intake_level"] = level
        if override:
            out[code] = override
    return out


def office_worker_intake_specs() -> list[dict[str, Any]]:
    return [
        _spec("recruitment.candidate.first_name", sort_order=10, intake_level=REQUIREMENT_REQUIRED),
        _spec("recruitment.candidate.last_name", sort_order=20, intake_level=REQUIREMENT_REQUIRED),
        _spec("recruitment.candidate.contacts.phone", sort_order=30, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_PHONE),
        _spec("recruitment.candidate.contacts.email", sort_order=40, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_EMAIL),
        _spec("platform.identity.citizenship", sort_order=50, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_SELECT),
        _spec("platform.identity.birth_date", sort_order=60, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_DATE),
        _spec("recruitment.candidate.personal.current_location", sort_order=70, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_SELECT),
        _spec("recruitment.candidate.experience.years_similar_role", sort_order=80, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_SELECT),
        _spec("recruitment.candidate.personal.residency_status", sort_order=90, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_SELECT),
    ]


def warehouse_worker_intake_specs() -> list[dict[str, Any]]:
    return [
        _spec("recruitment.candidate.first_name", sort_order=10, intake_level=REQUIREMENT_REQUIRED),
        _spec("recruitment.candidate.last_name", sort_order=20, intake_level=REQUIREMENT_REQUIRED),
        _spec("recruitment.candidate.contacts.phone", sort_order=30, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_PHONE),
        _spec("recruitment.candidate.contacts.email", sort_order=40, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_EMAIL),
        _spec("platform.identity.citizenship", sort_order=50, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_SELECT),
        _spec("recruitment.candidate.personal.current_location", sort_order=60, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_SELECT),
        _spec("recruitment.candidate.personal.residency_status", sort_order=70, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_SELECT),
        _spec("recruitment.candidate.qualifications.forklift_license", sort_order=80, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_YES_NO),
    ]


def driver_ce_intake_specs() -> list[dict[str, Any]]:
    return [
        _spec("recruitment.candidate.first_name", sort_order=10, intake_level=REQUIREMENT_REQUIRED),
        _spec("recruitment.candidate.last_name", sort_order=20, intake_level=REQUIREMENT_REQUIRED),
        _spec("recruitment.candidate.contacts.phone", sort_order=30, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_PHONE),
        _spec("recruitment.candidate.contacts.email", sort_order=40, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_EMAIL),
        _spec("platform.identity.citizenship", sort_order=50, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_SELECT),
        _spec("platform.identity.birth_date", sort_order=60, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_DATE),
        _spec("recruitment.candidate.personal.residency_status", sort_order=70, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_SELECT),
        _spec("recruitment.candidate.experience.years_ce", sort_order=80, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_SELECT),
        _spec("recruitment.candidate.experience.trailer_types[]", sort_order=90, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_MULTISELECT),
        _spec("recruitment.candidate.qualifications.eu_license_with_code_95", sort_order=100, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_YES_NO),
        _spec("recruitment.candidate.qualifications.tachograph_card", sort_order=110, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_YES_NO),
        _spec("recruitment.candidate.personal.has_adr", sort_order=120, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_YES_NO),
    ]


def general_candidate_intake_specs() -> list[dict[str, Any]]:
    return [
        _spec("recruitment.candidate.first_name", sort_order=10, intake_level=REQUIREMENT_REQUIRED),
        _spec("recruitment.candidate.last_name", sort_order=20, intake_level=REQUIREMENT_REQUIRED),
        _spec("recruitment.candidate.contacts.phone", sort_order=30, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_PHONE),
        _spec("recruitment.candidate.contacts.email", sort_order=40, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_EMAIL),
        _spec("platform.identity.citizenship", sort_order=50, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_SELECT),
        _spec("recruitment.candidate.personal.current_location", sort_order=60, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_SELECT),
        _spec("recruitment.candidate.personal.residency_status", sort_order=70, intake_level=REQUIREMENT_REQUIRED, widget_hint=WIDGET_SELECT),
        _spec("recruitment.candidate.experience.years_similar_role", sort_order=80, intake_level=REQUIREMENT_OPTIONAL, widget_hint=WIDGET_SELECT),
    ]


def specs_to_profile_fields(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "qualified_code": row["qualified_code"],
            "sort_order": row["sort_order"],
            "intake_level": row["intake_level"],
            "card_save_level": row.get("card_save_level") or row["intake_level"],
            "transition_level": row.get("transition_level") or REQUIREMENT_OPTIONAL,
        }
        for row in specs
    ]
