"""Executable intake mapping at Lead → Candidate conversion."""

from __future__ import annotations

from backend.app.modules.leads.conversion_mapping import (
    apply_executable_intake_mapping,
    attach_field_answer_labels,
    compact_executable_rules,
    conversion_payload_from_normalized,
)


def test_leftover_flat_keys_are_not_a_write_vocabulary() -> None:
    mapped = apply_executable_intake_mapping(
        {
            "in_poland": True,
            "experience_eu_years": 2,
            "phone": "+48111",
            "first_name": "Jan",
        }
    )
    assert mapped.extra.get("in_poland") is None
    assert mapped.personal.get("in_poland") is None
    assert mapped.extra.get("experience_eu_years") is None
    assert mapped.columns.get("phone") is None
    assert mapped.columns.get("first_name") is None


def test_canonical_facts_write_candidate_fields() -> None:
    mapped = apply_executable_intake_mapping(
        {
            "canonical_facts_v1": {
                "recruitment.candidate.personal.in_poland": True,
                "recruitment.candidate.experience.years_ce": 2,
                "recruitment.candidate.contacts.phone": "+48111",
                "recruitment.candidate.first_name": "Jan",
            }
        }
    )
    assert mapped.extra.get("in_poland") is True
    assert mapped.personal.get("in_poland") is True
    assert mapped.extra.get("experience_eu_years") == 2
    assert mapped.columns.get("phone") == "+48111"
    assert mapped.columns.get("first_name") == "Jan"


def test_executable_rules_write_unknown_candidate_qualified_to_extra() -> None:
    mapped = apply_executable_intake_mapping(
        {
            "field_answers": [{"name": "jaka_masz_kategorie", "values": ["C+E"]}],
            "mapping_applied_v1": {
                "executable_rules": [
                    {
                        "source": "jaka_masz_kategorie",
                        "qualified_field_code": "recruitment.candidate.personal.driving_license_category",
                        "normalized_target": "driving_license_category",
                    }
                ]
            },
        }
    )
    assert mapped.extra.get("driving_license_category") == "C+E"


def test_unmapped_answers_are_not_copied_to_candidate() -> None:
    mapped = apply_executable_intake_mapping(
        {
            "field_answers": [
                {"name": "custom_hobby", "values": ["chess"], "label": "Hobby"},
                {"name": "utm_source", "values": ["fb"]},
                {
                    "name": "inbox_url",
                    "values": ["https://business.facebook.com/latest/thread"],
                },
                {
                    "name": "какой у вас опыт работы водителем c+e в международных перевозках по ес?",
                    "values": ["1–2_года"],
                },
            ]
        }
    )
    assert "intake_answers_v1" not in mapped.extra
    assert "custom_hobby" not in mapped.extra
    assert "inbox_url" not in mapped.extra
    assert "inbox_url" not in mapped.columns


def test_technical_inbox_url_is_not_written_even_with_rule() -> None:
    mapped = apply_executable_intake_mapping(
        {
            "field_answers": [
                {"name": "inbox_url", "values": ["https://business.facebook.com/latest/thread"]},
            ],
            "mapping_applied_v1": {
                "executable_rules": [
                    {
                        "source": "inbox_url",
                        "normalized_target": "inbox_url",
                    }
                ]
            },
        }
    )
    assert "inbox_url" not in mapped.extra
    assert "intake_answers_v1" not in mapped.extra


def test_compact_rules_skip_lead_hints() -> None:
    rules = compact_executable_rules(
        [
            {"source": "vac", "target": "vacancy_id"},
            {"source": "phone", "qualified_field_code": "recruitment.candidate.contacts.phone"},
        ]
    )
    sources = [r["source"] for r in rules]
    assert "vac" not in sources
    assert "phone" in sources


def test_option_map_applies_graph_snake_case_to_candidate() -> None:
    mapped = apply_executable_intake_mapping(
        {
            "poland_stay_basis": "виза",
            "field_answers": [
                {"name": "основание_для_пребывания_в_польше", "values": ["виза"]},
                {"name": "опыт_работы_с/се_в_европе", "values": ["более_2_лет"]},
            ],
            "mapping_applied_v1": {
                "executable_rules": [
                    {
                        "source": "основание_для_пребывания_в_польше",
                        "normalized_target": "poland_stay_basis",
                        "qualified_field_code": "recruitment.candidate.personal.residency_status",
                    },
                    {
                        "source": "опыт_работы_с/се_в_европе",
                        "normalized_target": "experience_eu_years",
                        "qualified_field_code": "recruitment.candidate.experience.years_ce",
                    },
                ]
            },
            "ingest_envelope_v1": {
                "mapping_result": {
                    "accepted_rules": [
                        {
                            "source": "основание_для_пребывания_в_польше",
                            "qualified_field_code": "recruitment.candidate.personal.residency_status",
                            "option_map": {"Виза": "Wiza"},
                        },
                        {
                            "source": "опыт_работы_с/се_в_европе",
                            "qualified_field_code": "recruitment.candidate.experience.years_ce",
                            "option_map": {"Более 2 лет": "Więcej niż 2 lata"},
                        },
                    ]
                }
            },
        }
    )
    assert mapped.extra.get("poland_stay_basis") == "Wiza"
    assert mapped.personal.get("residency_status") == "Wiza"
    assert mapped.extra.get("experience_eu_years") == "Więcej niż 2 lata"


def test_conversion_payload_lands_mapped_licence_not_ignored_color() -> None:
    payload = conversion_payload_from_normalized(
        {
            "email": "anna@example.com",
            "field_answers": [
                {"name": "email", "values": ["anna@example.com"]},
                {"name": "which_licence", "values": ["CE"]},
                {"name": "favourite_color", "values": ["blue"]},
            ],
            "mapping_applied_v1": {
                "executable_rules": [
                    {
                        "source": "email",
                        "normalized_target": "email",
                        "qualified_field_code": "recruitment.candidate.contacts.email",
                    },
                    {
                        "source": "which_licence",
                        "normalized_target": "poland_stay_basis",
                        "qualified_field_code": "recruitment.candidate.personal.residency_status",
                    },
                ]
            },
        }
    )
    assert payload.get("email") == "anna@example.com"
    assert payload["extra"]["poland_stay_basis"] == "CE"
    assert payload["personal_data"]["residency_status"] == "CE"
    extra = payload.get("extra") or {}
    personal = payload.get("personal_data") or {}
    assert "favourite_color" not in extra
    assert "blue" not in extra.values()
    assert "blue" not in personal.values()


def test_attach_labels_from_rules() -> None:
    answers = [{"name": "jaka_masz_kategorie", "values": ["C+E"]}]
    attach_field_answer_labels(
        answers,
        [{"source": "jaka_masz_kategorie", "label": "Jaką masz kategorię?", "target": "phone"}],
    )
    assert answers[0]["label"] == "Jaką masz kategorię?"
