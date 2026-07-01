"""Recruitment module canonical fields and default card layouts."""

from __future__ import annotations

from typing import Any

from backend.app.field_registry.constants import (
    DEFAULT_CANDIDATE_LAYOUT_CODE,
    DEFAULT_VACANCY_LAYOUT_CODE,
    ENTITY_CANDIDATE,
    ENTITY_VACANCY,
    RECRUITMENT_MODULE,
)


def _candidate_field(
    field_code: str,
    *,
    field_type: str,
    name: str,
    storage: dict[str, Any],
    section: str,
    pii_class: str | None = None,
    reference_domain: str | None = None,
    legacy_aliases: list[str] | None = None,
) -> dict[str, Any]:
    qualified = f"recruitment.candidate.{field_code}"
    return {
        "qualified_code": qualified,
        "code": field_code.replace(".", "_").replace("[]", "_list"),
        "entity_type": ENTITY_CANDIDATE,
        "field_type": field_type,
        "name": name,
        "label_key": f"fields.recruitment_candidate_{field_code.replace('.', '_').replace('[]', '_list')}",
        "ownership": RECRUITMENT_MODULE,
        "pii_class": pii_class,
        "reference_domain": reference_domain,
        "storage": storage,
        "legacy_aliases": legacy_aliases or [field_code.split(".")[-1]],
        "default_section": section,
    }


def _vacancy_field(
    field_code: str,
    *,
    field_type: str,
    name: str,
    storage: dict[str, Any],
    section: str = "basic",
) -> dict[str, Any]:
    qualified = f"recruitment.vacancy.{field_code}"
    return {
        "qualified_code": qualified,
        "code": field_code,
        "entity_type": ENTITY_VACANCY,
        "field_type": field_type,
        "name": name,
        "label_key": f"fields.recruitment_vacancy_{field_code}",
        "ownership": RECRUITMENT_MODULE,
        "pii_class": None,
        "reference_domain": None,
        "storage": storage,
        "legacy_aliases": [field_code],
        "default_section": section,
    }


def recruitment_candidate_fields() -> list[dict[str, Any]]:
    return [
        _candidate_field("first_name", field_type="text", name="First name", storage={"kind": "column", "path": "first_name"}, section="basic", pii_class="identity"),
        _candidate_field("last_name", field_type="text", name="Last name", storage={"kind": "column", "path": "last_name"}, section="basic", pii_class="identity"),
        _candidate_field("contacts.phone_country_code", field_type="code", name="Phone country code", storage={"kind": "column", "path": "phone_country_code"}, section="basic", pii_class="contact", legacy_aliases=["phone_country_code"]),
        _candidate_field("contacts.phone", field_type="phone_e164", name="Phone", storage={"kind": "column", "path": "phone"}, section="basic", pii_class="contact", legacy_aliases=["phone"]),
        _candidate_field("contacts.email", field_type="email", name="Email", storage={"kind": "column", "path": "email"}, section="basic", pii_class="contact", legacy_aliases=["email"]),
        _candidate_field("contacts.preferred_messenger", field_type="code", name="Preferred messenger", storage={"kind": "json_path", "path": "contacts.preferred_messenger"}, section="basic", pii_class="contact", legacy_aliases=["preferred_messenger"]),
        _candidate_field("personal.residency_status", field_type="reference_code", name="Residency status", storage={"kind": "json_path", "path": "personal_data.residency_status"}, section="personal", reference_domain="legal_statuses", legacy_aliases=["residency_status"]),
        _candidate_field("personal.current_location", field_type="text", name="Current location", storage={"kind": "json_path", "path": "personal_data.current_location"}, section="personal", legacy_aliases=["current_location"]),
        _candidate_field("personal.in_poland", field_type="boolean", name="In Poland", storage={"kind": "json_path", "path": "personal_data.in_poland"}, section="personal", legacy_aliases=["in_poland"]),
        _candidate_field("experience.years_ce", field_type="integer", name="Years CE experience", storage={"kind": "json_path", "path": "extra.experience.years_ce"}, section="experience", legacy_aliases=["years_ce", "experience_eu_years"]),
        _candidate_field("experience.intl_experience", field_type="boolean", name="International experience", storage={"kind": "json_path", "path": "extra.experience.intl_experience"}, section="experience", legacy_aliases=["intl_experience"]),
        _candidate_field("experience.trailer_types[]", field_type="reference_code[]", name="Trailer types", storage={"kind": "json_path", "path": "extra.experience.trailer_types"}, section="experience", legacy_aliases=["trailer_types"]),
        _candidate_field("experience.route_types[]", field_type="reference_code[]", name="Route types", storage={"kind": "json_path", "path": "extra.experience.route_types"}, section="experience", legacy_aliases=["route_types"]),
        _candidate_field("employments[]", field_type="json_object", name="Employment history", storage={"kind": "json_path", "path": "extra.employments"}, section="employments", legacy_aliases=["employments", "employment_history"]),
        _candidate_field("agreements.general", field_type="boolean", name="General agreement", storage={"kind": "json_path", "path": "extra.agreements.general"}, section="agreements", legacy_aliases=["general", "privacy"]),
        _candidate_field("agreements.employer_share", field_type="boolean", name="Employer share consent", storage={"kind": "json_path", "path": "extra.agreements.employer_share"}, section="agreements", legacy_aliases=["employer_share", "contact"]),
        _candidate_field("agreements.terms_acceptance", field_type="boolean", name="Terms acceptance", storage={"kind": "json_path", "path": "extra.agreements.terms_acceptance"}, section="agreements"),
        _candidate_field("operations.stage", field_type="code", name="Pipeline stage", storage={"kind": "column", "path": "stage"}, section="operations", legacy_aliases=["stage"]),
    ]


def recruitment_vacancy_fields() -> list[dict[str, Any]]:
    return [
        _vacancy_field("title", field_type="text", name="Title", storage={"kind": "column", "path": "title"}),
        _vacancy_field("description", field_type="textarea", name="Description", storage={"kind": "column", "path": "description"}, section="details"),
        _vacancy_field("location", field_type="text", name="Location", storage={"kind": "column", "path": "location"}),
        _vacancy_field("employment_type", field_type="code", name="Employment type", storage={"kind": "column", "path": "employment_type"}),
        _vacancy_field("headcount_target", field_type="integer", name="Headcount target", storage={"kind": "column", "path": "headcount_target"}, section="operations"),
        _vacancy_field("company_id", field_type="code", name="Client company", storage={"kind": "column", "path": "company_id"}, section="operations"),
    ]


def _layout_field(qualified_code: str, *, section: str, order: int, required: bool = False) -> dict[str, Any]:
    return {
        "qualified_code": qualified_code,
        "section_code": section,
        "sort_order": order,
        "visible": True,
        "required": required,
    }


def recruitment_card_layouts() -> list[dict[str, Any]]:
    candidate_fields = recruitment_candidate_fields()
    candidate_layout_fields = []
    order = 10
    for row in candidate_fields:
        section = str(row.get("default_section") or "general")
        required = row["qualified_code"] in {
            "recruitment.candidate.first_name",
            "recruitment.candidate.last_name",
            "recruitment.candidate.contacts.phone",
        }
        candidate_layout_fields.append(
            _layout_field(row["qualified_code"], section=section, order=order, required=required)
        )
        order += 10

    identity_refs = [
        _layout_field("platform.identity.birth_date", section="personal", order=10),
        _layout_field("platform.identity.citizenship", section="personal", order=20, required=False),
        _layout_field("platform.identity.address", section="personal", order=30),
    ]

    vacancy_layout_fields = []
    v_order = 10
    for row in recruitment_vacancy_fields():
        section = str(row.get("default_section") or "basic")
        required = row["qualified_code"] == "recruitment.vacancy.title"
        vacancy_layout_fields.append(
            _layout_field(row["qualified_code"], section=section, order=v_order, required=required)
        )
        v_order += 10

    return [
        {
            "code": DEFAULT_CANDIDATE_LAYOUT_CODE,
            "name": "Recruitment candidate default card",
            "entity_type": ENTITY_CANDIDATE,
            "is_default": True,
            "fields": candidate_layout_fields + identity_refs,
        },
        {
            "code": DEFAULT_VACANCY_LAYOUT_CODE,
            "name": "Recruitment vacancy default card",
            "entity_type": ENTITY_VACANCY,
            "is_default": True,
            "fields": vacancy_layout_fields,
        },
    ]


def recruitment_module_manifest() -> dict[str, Any]:
    return {
        "module": RECRUITMENT_MODULE,
        "registry_version": "field_registry_v1",
        "canonical_fields": recruitment_candidate_fields() + recruitment_vacancy_fields(),
        "card_layouts": recruitment_card_layouts(),
    }
