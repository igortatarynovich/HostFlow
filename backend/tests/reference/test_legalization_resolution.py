"""Hub evidence confirms a legalization requirement. A file alone does not."""

from __future__ import annotations

from datetime import date

from backend.app.reference.legalization_catalog import resolve_legalization
from backend.app.reference.legalization_resolution import apply_hub_resolution, readiness_from_resolved
from backend.app.services.operator_facts_surface import apply_operator_facts_patch, empty_facts

TODAY = date(2026, 10, 12)


def _doc(code: str, **overrides):
    row = {
        "id": code,
        "type_code": code,
        "status": "approved",
        "has_file": True,
        "number": "N-1",
        "expire_date": "2030-01-01",
        "issue_date": "2024-01-01",
        "meta": {},
    }
    row.update(overrides)
    return row


def _resolve(patch: dict, documents: list[dict], *, employment: dict | None = None, base: dict | None = None):
    facts = apply_operator_facts_patch(base or empty_facts(), patch, employment_id="emp-1")
    stored = facts["employments"].get("emp-1") or facts["work"]
    facts = {**facts, "work": stored}
    if patch.get("stay_valid_from"):
        facts["stay_valid_from"] = patch["stay_valid_from"]
    reading = resolve_legalization(facts)
    return apply_hub_resolution(
        reading,
        documents,
        facts=facts,
        employment=employment or {"client_company_id": "employer-1"},
        today=TODAY,
    )


def test_poland_is_confirmed_without_a_permit_document() -> None:
    reading = _resolve({"citizenship": "PL"}, [])
    assert reading["resolved"]["residence"] == "confirmed"
    assert reading["resolved"]["work"] == "confirmed"
    assert reading["resolved"]["missing_residence"] == []
    assert reading["readiness"]["ready"] is True
    assert reading["readiness"]["blockers"] == []


def test_temporary_card_needs_an_approved_decision() -> None:
    facts = {"citizenship": "UA", "stay_basis": "karta_pobytu", "stay_card_kind": "temporary"}
    card = _doc("residence_card")
    missing = _resolve(facts, [card])
    assert missing["resolved"]["residence"] == "needs_document"
    assert missing["resolved"]["missing_residence"] == ["decision"]
    assert missing["readiness"]["ready"] is False

    uploaded = _resolve(facts, [_doc("residence_card", status="uploaded"), _doc("decision")])
    assert uploaded["resolved"]["residence"] == "needs_verification"

    rejected = _resolve(facts, [_doc("residence_card", status="rejected"), _doc("decision")])
    assert rejected["resolved"]["residence"] == "not_confirmed"

    expired = _resolve(facts, [_doc("residence_card", expire_date="2020-01-01"), _doc("decision")])
    assert expired["resolved"]["residence"] == "expired"

    incomplete = _resolve(facts, [_doc("residence_card", number=""), _doc("decision")])
    assert incomplete["resolved"]["residence"] == "needs_verification"

    both = _resolve(facts, [card, _doc("decision")])
    assert both["resolved"]["residence"] == "confirmed"
    assert both["resolved"]["work"] == "needs_permit"
    assert both["readiness"] == readiness_from_resolved(both["resolved"])


def test_presence_does_not_follow_a_stale_or_missing_file() -> None:
    facts = {"citizenship": "UA", "stay_basis": "visa_d", "visa_type": "D"}
    stale = _resolve(
        {**facts, "document_presence": {"visa": False}},
        [_doc("visa")],
    )
    assert stale["resolved"]["residence"] == "needs_document"
    assert stale["resolved"]["residence_detail"] == "stale_file"

    empty = _resolve(
        {**facts, "document_presence": {"visa": True}},
        [_doc("visa", has_file=False, status="missing")],
    )
    assert empty["resolved"]["residence_detail"] == "presence_without_file"


def test_visa_confirms_stay_and_still_asks_for_work() -> None:
    reading = _resolve(
        {"citizenship": "UA", "stay_basis": "visa_d", "visa_type": "D"},
        [_doc("visa", meta={"visa_type": "D"})],
    )
    assert reading["resolved"]["residence"] == "confirmed"
    assert reading["resolved"]["work"] == "needs_permit"
    assert reading["selected_stay"]["documents"] == ["visa"]


def test_visa_free_uses_the_passport_and_the_90_day_period() -> None:
    base = {"citizenship": "UA", "stay_basis": "visa_free"}
    missing = _resolve(base, [])
    assert missing["resolved"]["missing_residence"] == ["passport"]
    assert all(code != "visa_free" for code in missing["resolved"]["missing_residence"])

    too_long = _resolve(
        {**base, "stay_valid_from": "2026-01-01", "stay_valid_to": "2026-12-01"},
        [_doc("passport")],
    )
    assert too_long["resolved"]["residence"] == "not_confirmed"

    allowed = _resolve(
        {**base, "stay_valid_from": "2026-10-01", "stay_valid_to": "2026-12-01"},
        [_doc("passport")],
    )
    assert allowed["resolved"]["residence"] == "confirmed"


def test_work_permit_procedure_is_not_confirmation() -> None:
    base = {"citizenship": "UA", "stay_basis": "visa_d", "visa_type": "D", "work_label": "work_permit"}
    visa = _doc("visa")
    ordered = _resolve(base, [visa, _doc("work_permit", has_file=False, status="requested", ordered_at="2026-10-01", number="")])
    assert ordered["resolved"]["work"] == "ordered"

    received = _resolve(base, [visa, _doc("work_permit", has_file=False, status="received", number="")])
    assert received["resolved"]["work"] == "needs_document"

    reviewing = _resolve(base, [visa, _doc("work_permit", status="uploaded")])
    assert reviewing["resolved"]["work"] == "needs_verification"

    matched = _resolve(
        base,
        [visa, _doc("work_permit", meta={"client_company_id": "employer-1"})],
    )
    assert matched["resolved"]["residence"] == "confirmed"
    assert matched["resolved"]["work"] == "confirmed"
    assert matched["readiness"]["ready"] is True

    other = _resolve(
        base,
        [visa, _doc("work_permit", meta={"client_company_id": "other-employer"})],
    )
    assert other["resolved"]["work"] == "needs_review"
    assert other["resolved"]["work_detail"] == "employment_mismatch"

    lapsed = _resolve(base, [visa, _doc("work_permit", expire_date="2026-01-01")])
    assert lapsed["resolved"]["work"] == "expired"


def test_one_decision_can_confirm_conditional_work_without_a_second_copy() -> None:
    reading = _resolve(
        {
            "citizenship": "UA",
            "stay_basis": "karta_pobytu",
            "stay_card_kind": "temporary",
            "work_label": "included_in_stay",
        },
        [
            _doc("residence_card"),
            _doc("decision", meta={"work_allowed": True, "client_company_id": "employer-1"}),
        ],
    )
    assert reading["resolved"]["residence"] == "confirmed"
    assert reading["resolved"]["work"] == "confirmed"
    assert [row["id"] for row in [_doc("decision")]].count("decision") == 1


def test_permanent_stay_confirms_work_only_after_its_own_evidence() -> None:
    patch = {"citizenship": "UA", "stay_basis": "karta_pobytu", "stay_card_kind": "permanent"}
    open_case = _resolve(patch, [_doc("residence_card")])
    assert open_case["resolved"]["residence"] != "confirmed"
    assert open_case["resolved"]["work"] != "confirmed"

    closed = _resolve(patch, [_doc("residence_card"), _doc("decision")])
    assert closed["resolved"]["residence"] == "confirmed"
    assert closed["resolved"]["work"] == "confirmed"


def test_override_is_not_confirmation_until_the_exemption_is_proven() -> None:
    claimed = _resolve({"citizenship": "UA", "stay_required": False, "work_required": False, "stay_exemption": "other", "work_exemption": "other"}, [])
    assert claimed["selection"]["stay_manual"] is True
    assert claimed["resolved"]["residence"] == "needs_verification"
    assert claimed["resolved"]["work"] == "needs_verification"
    assert claimed["readiness"]["ready"] is False

    proven = _resolve(
        {
            "citizenship": "UA",
            "stay_required": False,
            "work_required": False,
            "stay_exemption": "permanent_stay",
            "work_exemption": "permanent_stay",
        },
        [_doc("residence_card", meta={"residence_permit_type": "permanent"}), _doc("decision")],
    )
    assert proven["resolved"]["residence"] == "confirmed"
    assert proven["resolved"]["work"] == "confirmed"


def test_an_unlisted_basis_confirms_only_through_its_evidence_contract() -> None:
    reading = {
        "resolved": {"residence": "needs_document", "work": "needs_permit"},
        "selection": {"stay_required": True, "work_required": True, "stay_manual": False, "work_manual": False},
        "selected_stay": {
            "code": "future_basis",
            "confirm": "evidence",
            "stay_bases": ["future_basis"],
            "evidence": [{"label": "future_card", "codes": ["future_card"], "metadata": ["number", "expire_date"]}],
            "validity_rules": [],
            "work_effect": "none",
        },
    }
    resolved = apply_hub_resolution(
        reading,
        [_doc("future_card")],
        facts={"citizenship": "UA", "work": {}},
        employment={},
        today=TODAY,
    )
    assert resolved["resolved"]["residence"] == "confirmed"
    assert resolved["resolved"]["missing_residence"] == []


def test_changing_citizenship_does_not_confirm_the_old_document() -> None:
    ukrainian = apply_operator_facts_patch(empty_facts(), {"citizenship": "UA", "stay_basis": "visa_d"}, employment_id="emp-1")
    polish = apply_operator_facts_patch(ukrainian, {"citizenship": "PL"}, employment_id="emp-1")
    reading = resolve_legalization(polish)
    resolved = apply_hub_resolution(reading, [_doc("visa")], facts=polish, employment={}, today=TODAY)
    assert polish["stay_basis"] == "visa_d"
    assert resolved["resolved"]["residence"] == "needs_review"
    assert resolved["readiness"]["ready"] is False
