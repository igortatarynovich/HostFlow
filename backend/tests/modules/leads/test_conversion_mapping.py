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


def test_unmapped_answers_stay_on_intake_answers() -> None:
    mapped = apply_executable_intake_mapping(
        {
            "field_answers": [
                {"name": "custom_hobby", "values": ["chess"], "label": "Hobby"},
                {"name": "utm_source", "values": ["fb"]},
            ]
        }
    )
    answers = mapped.extra.get("intake_answers_v1") or []
    names = [a["name"] for a in answers]
    assert "custom_hobby" in names
    assert "utm_source" not in names


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
