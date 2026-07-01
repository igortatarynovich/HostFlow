"""P10A — Presentation Rules Runtime unit tests."""

from __future__ import annotations

import pytest

from backend.app.entity_profile.presentation_rules import (
    PresentationRulesWriteError,
    evaluate_presentation_field_state,
    evaluate_rule_condition,
    missing_required_presentation_fields,
    validate_presentation_rules_for_subset,
)


def _field(code: str, level: str = "optional", rules: dict | None = None) -> dict:
    override: dict = {"intake_level": level}
    if rules:
        override["presentation_rules"] = rules
    row = {
        "qualified_code": code,
        "intake_level": level,
        "presentation_overrides": override,
    }
    if rules:
        row["presentation_rules"] = rules
    return row


def test_p10a_show_if_hides_field_when_false() -> None:
    field = _field(
        "recruitment.candidate.contacts.email",
        "optional",
        {"show_if": {"source_field": "recruitment.candidate.first_name", "operator": "truthy"}},
    )
    hidden = evaluate_presentation_field_state(field, {})
    assert hidden["visible"] is False
    assert hidden["intake_level"] == "hidden"

    shown = evaluate_presentation_field_state(field, {"recruitment.candidate.first_name": "Jan"})
    assert shown["visible"] is True


def test_p10a_hide_if() -> None:
    field = _field(
        "recruitment.candidate.last_name",
        "optional",
        {"hide_if": {"source_field": "recruitment.candidate.first_name", "operator": "eq", "value": "skip"}},
    )
    assert evaluate_presentation_field_state(field, {"recruitment.candidate.first_name": "skip"})["visible"] is False
    assert evaluate_presentation_field_state(field, {"recruitment.candidate.first_name": "Jan"})["visible"] is True


def test_p10a_required_if() -> None:
    field = _field(
        "recruitment.candidate.contacts.email",
        "optional",
        {
            "show_if": {"source_field": "recruitment.candidate.first_name", "operator": "truthy"},
            "required_if": {"source_field": "recruitment.candidate.first_name", "operator": "truthy"},
        },
    )
    state = evaluate_presentation_field_state(field, {"recruitment.candidate.first_name": "Anna"})
    assert state["visible"] is True
    assert state["intake_level"] == "required"


def test_p10a_readonly_if() -> None:
    field = _field(
        "recruitment.candidate.first_name",
        "optional",
        {"readonly_if": {"source_field": "recruitment.candidate.last_name", "operator": "truthy"}},
    )
    assert evaluate_presentation_field_state(field, {})["readonly"] is False
    assert evaluate_presentation_field_state(field, {"recruitment.candidate.last_name": "Kowalski"})["readonly"] is True


def test_p10a_validate_source_outside_subset() -> None:
    overrides = {
        "recruitment.candidate.contacts.email": {
            "intake_level": "optional",
            "presentation_rules": {
                "show_if": {
                    "source_field": "platform.identity.citizenship",
                    "operator": "truthy",
                }
            },
        }
    }
    subset = [
        "recruitment.candidate.first_name",
        "recruitment.candidate.contacts.email",
    ]
    with pytest.raises(PresentationRulesWriteError) as exc:
        validate_presentation_rules_for_subset(overrides, subset)
    assert exc.value.code == "presentation_rule_source_outside_subset"


def test_p10a_missing_required_respects_visibility() -> None:
    presentation = {
        "fields": [
            _field("recruitment.candidate.first_name", "required"),
            _field(
                "recruitment.candidate.contacts.email",
                "optional",
                {
                    "show_if": {"source_field": "recruitment.candidate.first_name", "operator": "truthy"},
                    "required_if": {"source_field": "recruitment.candidate.first_name", "operator": "truthy"},
                },
            ),
        ]
    }
    missing = missing_required_presentation_fields(
        presentation,
        {"recruitment.candidate.first_name": "Jan"},
    )
    assert "recruitment.candidate.first_name" not in missing
    assert "recruitment.candidate.contacts.email" in missing

    hidden_missing = missing_required_presentation_fields(presentation, {})
    assert "recruitment.candidate.contacts.email" not in hidden_missing


def test_p10a_evaluate_rule_condition_in_operator() -> None:
    assert evaluate_rule_condition(
        {"source_field": "recruitment.candidate.personal.in_poland", "operator": "in", "value": ["yes", "true"]},
        {"recruitment.candidate.personal.in_poland": "yes"},
    )
