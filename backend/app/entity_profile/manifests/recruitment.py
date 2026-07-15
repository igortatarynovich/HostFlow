"""Recruitment Entity Profile manifests."""

from __future__ import annotations

from typing import Any

from backend.app.entity_profile.constants import (
    DRIVER_CE_INTAKE_PRESENTATION_CODE,
    DRIVER_CE_PROFILE_CODE,
    DRIVER_CE_UA_INTAKE_PRESENTATION_CODE,
    DRIVER_CE_UA_PROFILE_CODE,
    ENTITY_CANDIDATE,
    RECRUITMENT_MODULE,
    REQUIREMENT_OPTIONAL,
    REQUIREMENT_REQUIRED,
    WAREHOUSE_WORKER_INTAKE_PRESENTATION_CODE,
    WAREHOUSE_WORKER_PROFILE_CODE,
)
from backend.app.field_registry.constants import DEFAULT_CANDIDATE_LAYOUT_CODE
from backend.app.process_engine.manifests.recruitment import DEFAULT_PROFILE_CODE as RECRUITMENT_DEFAULT_PROCESS_PROFILE


def _profile_field(
    qualified_code: str,
    *,
    sort_order: int,
    intake_level: str = REQUIREMENT_OPTIONAL,
    card_save_level: str = REQUIREMENT_OPTIONAL,
    transition_level: str = REQUIREMENT_OPTIONAL,
) -> dict[str, Any]:
    return {
        "qualified_code": qualified_code,
        "sort_order": sort_order,
        "intake_level": intake_level,
        "card_save_level": card_save_level,
        "transition_level": transition_level,
    }


def recruitment_candidate_driver_ce_profile() -> dict[str, Any]:
    """Driver C+E candidate — canonical field composition for intake and card."""
    return {
        "profile_code": DRIVER_CE_PROFILE_CODE,
        "entity_type": ENTITY_CANDIDATE,
        "module_owner": RECRUITMENT_MODULE,
        "name": "Driver Candidate (C+E)",
        "description": "Canonical field composition for driver C+E recruitment profile.",
        "default_layout_code": DEFAULT_CANDIDATE_LAYOUT_CODE,
        "document_pack_code": "recruitment.driver_ce_documents",
        "process_profile_code": RECRUITMENT_DEFAULT_PROCESS_PROFILE,
        "config": {
            "legacy_candidate_profile_code": "driver_ce_default",
        },
        "fields": [
            _profile_field(
                "recruitment.candidate.first_name",
                sort_order=10,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.last_name",
                sort_order=20,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.contacts.phone",
                sort_order=30,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.contacts.email",
                sort_order=40,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
            _profile_field(
                "platform.identity.citizenship",
                sort_order=50,
                intake_level=REQUIREMENT_OPTIONAL,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "platform.identity.birth_date",
                sort_order=60,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
            _profile_field(
                "platform.identity.address",
                sort_order=65,
                intake_level=REQUIREMENT_OPTIONAL,
                card_save_level=REQUIREMENT_REQUIRED,
                transition_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.experience.years_ce",
                sort_order=70,
                intake_level=REQUIREMENT_OPTIONAL,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.experience.trailer_types[]",
                sort_order=80,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
            _profile_field(
                "recruitment.candidate.experience.route_types[]",
                sort_order=90,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
            _profile_field(
                "recruitment.candidate.personal.in_poland",
                sort_order=100,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
        ],
        "intake_presentations": [
            {
                "presentation_code": DRIVER_CE_INTAKE_PRESENTATION_CODE,
                "field_subset": [
                    "recruitment.candidate.first_name",
                    "recruitment.candidate.last_name",
                    "recruitment.candidate.contacts.phone",
                ],
                "presentation_overrides": {
                    "recruitment.candidate.first_name": {"label_override": "Imię"},
                    "recruitment.candidate.last_name": {"label_override": "Nazwisko"},
                    "recruitment.candidate.contacts.phone": {"label_override": "Telefon"},
                },
            },
        ],
    }


def recruitment_candidate_warehouse_worker_profile() -> dict[str, Any]:
    """Warehouse worker — role variant without driver-specific experience fields."""
    return {
        "profile_code": WAREHOUSE_WORKER_PROFILE_CODE,
        "entity_type": ENTITY_CANDIDATE,
        "module_owner": RECRUITMENT_MODULE,
        "name": "Warehouse Worker Candidate",
        "description": "Role profile for warehouse/logistics candidates (non-driver).",
        "default_layout_code": DEFAULT_CANDIDATE_LAYOUT_CODE,
        "document_pack_code": "recruitment.warehouse_worker_documents",
        "process_profile_code": RECRUITMENT_DEFAULT_PROCESS_PROFILE,
        "config": {
            "role_variant": "warehouse_worker",
            "market_country": "PL",
        },
        "fields": [
            _profile_field(
                "recruitment.candidate.first_name",
                sort_order=10,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.last_name",
                sort_order=20,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.contacts.phone",
                sort_order=30,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.contacts.email",
                sort_order=40,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
            _profile_field(
                "platform.identity.citizenship",
                sort_order=50,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.personal.in_poland",
                sort_order=60,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
            _profile_field(
                "recruitment.candidate.personal.current_location",
                sort_order=70,
                intake_level=REQUIREMENT_OPTIONAL,
                card_save_level=REQUIREMENT_OPTIONAL,
            ),
            _profile_field(
                "recruitment.candidate.personal.residency_status",
                sort_order=80,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
        ],
        "intake_presentations": [
            {
                "presentation_code": WAREHOUSE_WORKER_INTAKE_PRESENTATION_CODE,
                "field_subset": [
                    "recruitment.candidate.first_name",
                    "recruitment.candidate.last_name",
                    "recruitment.candidate.contacts.phone",
                    "platform.identity.citizenship",
                ],
                "presentation_overrides": {
                    "recruitment.candidate.first_name": {"label_override": "Imię"},
                    "recruitment.candidate.last_name": {"label_override": "Nazwisko"},
                    "recruitment.candidate.contacts.phone": {"label_override": "Telefon"},
                    "platform.identity.citizenship": {"label_override": "Obywatelstwo"},
                },
            },
        ],
    }


def recruitment_candidate_driver_ce_ua_profile() -> dict[str, Any]:
    """Driver C+E — country variant (UA citizenship, PL market)."""
    return {
        "profile_code": DRIVER_CE_UA_PROFILE_CODE,
        "entity_type": ENTITY_CANDIDATE,
        "module_owner": RECRUITMENT_MODULE,
        "name": "Driver Candidate (C+E, UA)",
        "description": "Driver C+E profile for Ukrainian candidates in the PL recruitment market.",
        "default_layout_code": DEFAULT_CANDIDATE_LAYOUT_CODE,
        "document_pack_code": "recruitment.driver_ce_documents",
        "process_profile_code": RECRUITMENT_DEFAULT_PROCESS_PROFILE,
        "config": {
            "role_variant": "driver_ce",
            "market_country": "PL",
            "source_citizenship_default": "UA",
            "legacy_candidate_profile_code": "driver_ce_default",
        },
        "fields": [
            _profile_field(
                "recruitment.candidate.first_name",
                sort_order=10,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.last_name",
                sort_order=20,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.contacts.phone",
                sort_order=30,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.contacts.email",
                sort_order=40,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
            _profile_field(
                "platform.identity.citizenship",
                sort_order=50,
                intake_level=REQUIREMENT_REQUIRED,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "platform.identity.birth_date",
                sort_order=60,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
            _profile_field(
                "recruitment.candidate.experience.years_ce",
                sort_order=70,
                intake_level=REQUIREMENT_OPTIONAL,
                card_save_level=REQUIREMENT_REQUIRED,
            ),
            _profile_field(
                "recruitment.candidate.personal.in_poland",
                sort_order=80,
                intake_level=REQUIREMENT_OPTIONAL,
            ),
        ],
        "intake_presentations": [
            {
                "presentation_code": DRIVER_CE_UA_INTAKE_PRESENTATION_CODE,
                "field_subset": [
                    "recruitment.candidate.first_name",
                    "recruitment.candidate.last_name",
                    "recruitment.candidate.contacts.phone",
                    "platform.identity.citizenship",
                ],
                "presentation_overrides": {
                    "recruitment.candidate.first_name": {"label_override": "Imię"},
                    "recruitment.candidate.last_name": {"label_override": "Nazwisko"},
                    "recruitment.candidate.contacts.phone": {"label_override": "Telefon"},
                    "platform.identity.citizenship": {"label_override": "Obywatelstwo"},
                },
            },
        ],
    }


def recruitment_module_entity_profiles() -> list[dict[str, Any]]:
    return [
        recruitment_candidate_driver_ce_profile(),
        recruitment_candidate_warehouse_worker_profile(),
        recruitment_candidate_driver_ce_ua_profile(),
    ]
