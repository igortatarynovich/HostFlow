"""Legalization applicability. Citizenship recommends. The operator can disagree."""

from __future__ import annotations

from backend.app.reference.legalization_catalog import resolve_legalization
from backend.app.services.operator_facts_surface import apply_operator_facts_patch, empty_facts


def _facts(patch: dict, base: dict | None = None) -> dict:
    return apply_operator_facts_patch(base or empty_facts(), patch, employment_id="emp-1")


def test_polish_and_german_citizenship_recommend_no_and_confirm_the_regime() -> None:
    pl = resolve_legalization(_facts({"citizenship": "PL"}))
    assert pl["recommendation"] == {"stay_required": False, "work_required": False, "reason": "citizenship_pl"}
    assert pl["selection"]["stay_required"] is False
    assert pl["selection"]["work_required"] is False
    assert pl["selection"]["stay_manual"] is False
    assert pl["resolved"] == {"residence": "confirmed", "work": "confirmed"}
    assert pl["applicable_stay"] == []

    de = resolve_legalization(_facts({"citizenship": "DE"}))
    assert de["recommendation"]["reason"] == "citizenship_eu_eea_ch"
    assert de["resolved"]["residence"] == "confirmed"
    assert de["resolved"]["work"] == "confirmed"


def test_ukrainian_without_facts_starts_at_yes_and_offers_regimes_without_a_fake_document() -> None:
    reading = resolve_legalization(_facts({"citizenship": "UA"}))
    assert reading["recommendation"]["stay_required"] is True
    assert reading["recommendation"]["work_required"] is True
    codes = {item["code"] for item in reading["applicable_stay"]}
    assert {"visa", "visa_free", "temporary", "permanent", "eu_long_term", "special_protection"} <= codes
    assert "withdrawal_agreement" not in codes
    visa_free = next(item for item in reading["applicable_stay"] if item["code"] == "visa_free")
    assert visa_free["kind"] == "regime"
    assert visa_free["documents"] == []
    assert "schengen_90_180" in visa_free["validity_rules"]
    assert "oswiadczenie" in {item["code"] for item in reading["applicable_work"]}


def test_operator_can_turn_a_ukrainian_requirement_off_without_confirming_it() -> None:
    reading = resolve_legalization(_facts({"citizenship": "UA", "stay_required": False, "work_required": False}))
    assert reading["selection"]["stay_manual"] is True
    assert reading["selection"]["work_manual"] is True
    assert reading["operator"]["stay_required"] is False
    assert reading["resolved"]["residence"] == "needs_verification"
    assert reading["resolved"]["work"] == "needs_verification"
    assert reading["applicable_stay"] == []


def test_override_survives_a_later_unrelated_patch() -> None:
    saved = _facts({"citizenship": "UA", "stay_required": False})
    again = _facts({"stay_valid_to": "2026-12-01"}, base=saved)
    reading = resolve_legalization(again)
    assert reading["operator"]["stay_required"] is False
    assert reading["selection"]["stay_manual"] is True


def test_polish_operator_can_open_the_workflow() -> None:
    reading = resolve_legalization(_facts({"citizenship": "PL", "stay_required": True, "work_required": True}))
    assert reading["selection"]["stay_manual"] is True
    assert reading["selection"]["work_manual"] is True
    assert [item["code"] for item in reading["applicable_stay"]] == ["other"]
    assert reading["resolved"]["residence"] == "needs_document"
    assert "work_permit" in {item["code"] for item in reading["applicable_work"]}
    assert "oswiadczenie" not in {item["code"] for item in reading["applicable_work"]}


def test_residence_card_keeps_the_decision_and_does_not_confirm_work() -> None:
    temporary = resolve_legalization(_facts({
        "citizenship": "UA",
        "stay_basis": "karta_pobytu",
        "stay_card_kind": "temporary",
    }))
    card = temporary["selected_stay"]
    assert card["code"] == "temporary"
    assert "decision" in card["dependent_documents"]
    assert temporary["recommendation"]["work_required"] is True
    assert temporary["resolved"]["work"] == "needs_permit"

    permanent = resolve_legalization(_facts({
        "citizenship": "UA",
        "stay_basis": "karta_pobytu",
        "stay_card_kind": "permanent",
    }))
    assert permanent["recommendation"]["work_required"] is False
    assert permanent["resolved"]["work"] == "needs_verification"
    assert permanent["resolved"]["residence"] == "needs_document"

    resident = resolve_legalization(_facts({
        "citizenship": "UA",
        "stay_basis": "karta_pobytu",
        "stay_card_kind": "eu_long_term",
    }))
    assert resident["recommendation"]["reason"] == "eu_long_term_pl"
    assert resident["resolved"]["work"] == "needs_verification"


def test_visa_is_one_basis_with_a_c_or_d_type() -> None:
    reading = resolve_legalization(_facts({"citizenship": "UA", "stay_basis": "visa_d", "visa_type": "D"}))
    assert reading["selection"]["stay_code"] == "visa"
    assert reading["selection"]["visa_type"] == "D"
    assert reading["selected_stay"]["documents"] == ["visa"]
    switched = resolve_legalization(_facts({"visa_type": "C"}, base=_facts({"citizenship": "UA", "stay_basis": "visa_d"})))
    assert switched["selection"]["stay_code"] == "visa"
    assert switched["operator"]["stay_basis"] == "visa_c"


def test_british_citizenship_is_not_eu_until_withdrawal_is_recorded() -> None:
    plain = resolve_legalization(_facts({"citizenship": "GB"}))
    assert plain["recommendation"]["stay_required"] is True
    assert plain["recommendation"]["work_required"] is True
    assert "withdrawal_agreement" in {item["code"] for item in plain["applicable_stay"]}

    agreed = resolve_legalization(_facts({"citizenship": "GB", "stay_basis": "withdrawal_agreement"}))
    assert agreed["selection"]["stay_code"] == "withdrawal_agreement"
    assert agreed["selected_stay"]["kind"] == "regime"
    assert agreed["selected_stay"]["documents"] == []
    assert agreed["recommendation"]["work_required"] is False
    assert agreed["resolved"]["residence"] == "needs_verification"
    assert agreed["resolved"]["work"] == "needs_verification"


def test_changing_citizenship_keeps_the_basis_and_asks_for_review() -> None:
    ukrainian = _facts({"citizenship": "UA", "stay_basis": "visa_d"})
    polish = _facts({"citizenship": "PL"}, base=ukrainian)
    assert polish["stay_basis"] == "visa_d"
    reading = resolve_legalization(polish)
    assert reading["resolved"]["residence"] == "needs_review"
    assert reading["recommendation"]["stay_required"] is False


def test_ordered_permit_keeps_its_procedure() -> None:
    base = _facts({"citizenship": "UA", "stay_basis": "visa_d"})
    ordered = _facts({"work_label": "work_permit"}, base=base)
    reading = resolve_legalization({**ordered, "work": ordered["employments"]["emp-1"]})
    assert reading["selection"]["work_required"] is True
    assert reading["resolved"]["work"] == "needs_permit"
    assert ordered["employments"]["emp-1"]["procedure_type"] == "work_permit_a"
