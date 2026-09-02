"""Executable intake mapping at Lead → Candidate conversion."""

from __future__ import annotations

from backend.app.modules.leads.conversion_mapping import (
    apply_executable_intake_mapping,
    attach_field_answer_labels,
    compact_executable_rules,
)


def test_registry_copies_in_poland_and_experience() -> None:
    mapped = apply_executable_intake_mapping(
        {
            "in_poland": True,
            "experience_eu_years": 2,
            "phone": "+48111",
            "first_name": "Jan",
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


def test_attach_labels_from_rules() -> None:
    answers = [{"name": "jaka_masz_kategorie", "values": ["C+E"]}]
    attach_field_answer_labels(
        answers,
        [{"source": "jaka_masz_kategorie", "label": "Jaką masz kategorię?", "target": "phone"}],
    )
    assert answers[0]["label"] == "Jaką masz kategorię?"
