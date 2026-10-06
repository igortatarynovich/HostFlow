"""Operator Facts Surface runtime. Four operator scenarios, no new vocabulary."""

from __future__ import annotations

from datetime import date

from backend.app.services.operator_facts_surface import (
    apply_operator_facts_patch,
    build_operator_facts_view,
    chain_reading,
    drop_withheld_document_codes,
    empty_facts,
    project_required_document_types,
    requirement_codes_for_operator,
)

_UNCONDITIONAL = [
    "driver_license",
    "code95",
    "tacho_card",
    "medical_certificate",
    "psychotest",
    "visa",
    "work_permit",
    "residence_permit",
]


_CE_REQUIREMENTS = [
    {"requirement_code": "ce", "level": "REQUIRED"},
    {"requirement_code": "code95", "level": "REQUIRED"},
]


def _view(
    patch: dict,
    *,
    base: dict | None = None,
    today: date | None = None,
    requirements: list | None = None,
) -> tuple:
    facts = apply_operator_facts_patch(base or empty_facts(), patch, employment_id="emp-1")
    return (
        build_operator_facts_view(
            facts,
            employment_id="emp-1",
            today=today,
            requirements=requirements,
        ),
        facts,
    )


def _step(view: dict, key: str) -> dict:
    return next(step for step in view["steps"] if step["key"] == key)


def test_pl_and_eu_hide_stay_and_work_and_do_not_ask_for_those_files() -> None:
    view, facts = _view({"citizenship": "PL"})
    assert view["citizenship_class"] == "pl"
    assert view["chain"] == {
        "citizenship_class": "pl",
        "stay_basis": "not_required",
        "work_authorization_basis": "not_required",
        "valid_for_this_employment": "yes",
    }
    assert _step(view, "stay_basis")["visible"] is False
    assert _step(view, "work")["visible"] is False
    assert "unknown" not in view["chain"].values()
    asked = project_required_document_types(_UNCONDITIONAL, facts, employment_id="emp-1")
    assert "national_identity_card" not in asked
    assert "passport" not in asked
    assert "temporary_residence_decision" not in asked
    assert "driver_license" not in asked
    assert "visa" in asked
    assert "work_permit" in asked

    eu, eu_facts = _view({"citizenship": "DE"})
    assert eu["citizenship_class"] == "eu_eea_ch"
    assert eu["chain"]["stay_basis"] == "not_required"
    assert eu["chain"]["valid_for_this_employment"] == "yes"
    assert _step(eu, "stay_basis")["visible"] is False
    ch, _ = _view({"citizenship": "CH"})
    assert ch["citizenship_class"] == "eu_eea_ch"
    assert facts["stay_basis"] is None
    assert eu_facts["work"]["work_authorization_basis"] is None


def test_third_country_needs_input_does_not_ask_for_a_file() -> None:
    view, facts = _view({"citizenship": "BY"})
    assert view["citizenship_class"] == "third_country"
    assert view["chain"]["stay_basis"] is None
    assert view["chain"]["work_authorization_basis"] is None
    assert _step(view, "stay_basis")["visible"] is True
    assert _step(view, "work")["visible"] is False
    assert view["asks_file"] is False
    asked = project_required_document_types(_UNCONDITIONAL, facts, employment_id="emp-1")
    assert "passport" not in asked
    assert "national_identity_card" not in asked
    assert "temporary_residence_decision" not in asked
    assert "driver_license" not in asked
    assert "visa" in asked

    visa, _ = _view({"stay_basis": "visa_d"}, base=facts)
    assert _step(visa, "work")["visible"] is True
    assert visa["chain"]["stay_basis"] == "visa_d"

    unknown, unknown_facts = _view({"citizenship": "unknown"})
    assert unknown["citizenship_class"] is None
    assert unknown_facts["citizenship"] is None
    assert _step(unknown, "stay_basis")["visible"] is False
    assert chain_reading(unknown_facts)["citizenship_class"] is None


def test_work_permit_and_oswiadczenie_project_onto_existing_values() -> None:
    base = apply_operator_facts_patch(
        empty_facts(),
        {"citizenship": "BY", "stay_basis": "karta_pobytu"},
        employment_id="emp-1",
    )
    permit, permit_facts = _view({"work_label": "work_permit"}, base=base)
    assert permit["chain"]["work_authorization_basis"] == "separate_required"
    assert permit["chain"]["valid_for_this_employment"] == "operator_verification"
    stored = permit_facts["employments"]["emp-1"]
    assert stored["procedure_type"] == "work_permit_a"
    assert stored["work_authorization_basis"] == "separate_required"
    assert "oswiadczenie" not in stored.values()
    assert "zezwolenie_A" not in stored.values()

    declaration, declaration_facts = _view({"work_label": "oswiadczenie"}, base=base)
    decl = declaration_facts["employments"]["emp-1"]
    assert declaration["chain"]["work_authorization_basis"] == "separate_required"
    assert decl["procedure_type"] == "employer_declaration"
    assert "declaration" not in decl.values()

    included, _ = _view({"work_label": "included_in_stay"}, base=base)
    assert included["chain"]["work_authorization_basis"] == "included_in_stay"
    assert included["chain"]["valid_for_this_employment"] == "operator_verification"

    refused, _ = _view(
        {"work_label": "work_permit", "valid_for_this_employment": "no"},
        base=base,
    )
    assert refused["chain"]["valid_for_this_employment"] == "no"
    karta_asked = project_required_document_types(_UNCONDITIONAL, permit_facts, employment_id="emp-1")
    assert "residence_card" in karta_asked
    assert "decision" in karta_asked
    assert karta_asked.count("work_permit") == 1

    confirmed, confirmed_facts = _view(
        {
            "tachograph_presence": True,
            "adr_presence": True,
            "medical_presence": True,
            "psych_presence": True,
            "additional_presence": True,
        },
        base=base,
    )
    confirmed_asked = project_required_document_types(_UNCONDITIONAL, confirmed_facts, employment_id="emp-1")
    plain_asked = project_required_document_types(_UNCONDITIONAL, base, employment_id="emp-1")
    assert "decision" in confirmed_asked
    assert "medical_certificate" in confirmed_asked
    assert "psychological_certificate" in confirmed_asked
    assert "decision" in plain_asked
    for code in ("adr_certificate", "passport", "temporary_residence_decision", "additional_document"):
        assert code not in confirmed_asked
    assert confirmed["upload_codes"] == []

    dated, dated_facts = _view(
        {
            "work_label": "oswiadczenie",
            "authorization_valid_from": "2026-03-01",
            "authorization_valid_to": "2026-08-31",
            "authorization_conditions": "kierowca CE",
            "stay_valid_to": "2027-01-15",
        },
        base=base,
    )
    stored_decl = dated_facts["employments"]["emp-1"]
    assert stored_decl["valid_from"] == "2026-03-01"
    assert stored_decl["valid_to"] == "2026-08-31"
    assert stored_decl["conditions"] == "kierowca CE"
    assert dated_facts["stay_valid_to"] == "2027-01-15"
    assert _step(dated, "work")["operator_label"] == "oswiadczenie"
    assert "employer_declaration" == stored_decl["procedure_type"]

    free, _ = _view({"work_label": "not_required"}, base=base)
    assert free["chain"]["work_authorization_basis"] == "not_required"
    assert free["chain"]["valid_for_this_employment"] == "yes"
    assert _step(free, "work")["operator_label"] == "not_required"

    missing, _ = _view({"work_label": "no_right"}, base=base)
    assert missing["chain"]["work_authorization_basis"] is None
    assert missing["chain"]["valid_for_this_employment"] == "no"
    assert _step(missing, "work")["operator_label"] == "no_right"


def test_ce_code95_unknown_country_asks_no_file_then_shared_or_separate() -> None:
    base = apply_operator_facts_patch(empty_facts(), {"citizenship": "PL"}, employment_id="emp-1")
    unknown, unknown_facts = _view(
        {"licence_issuing_country": "unknown"},
        base=base,
        requirements=_CE_REQUIREMENTS,
    )
    ce = unknown["ce_code95"]
    assert ce["progress"] == "needs_input"
    assert ce["evidence_shape"] is None
    assert ce["asks_file"] is False
    assert ce["upload_codes"] == []
    assert ce["ce"]["resolution"] == "unresolved"
    assert ce["ce"]["holds_entrance"] is True
    asked = project_required_document_types(_UNCONDITIONAL, unknown_facts, employment_id="emp-1")
    assert "driver_license" not in asked
    assert "driver_qualification_card" not in asked
    assert "tachograph_card" not in project_required_document_types(
        ["driver_license", "code95"],
        unknown_facts,
        employment_id="emp-1",
    )

    shared, shared_facts = _view(
        {"licence_issuing_country": "PL"},
        base=base,
        requirements=_CE_REQUIREMENTS,
    )
    assert shared["ce_code95"]["evidence_shape"] == "shared"
    assert shared["ce_code95"]["evidence_variant"] == "combined_eu_license"
    assert shared["ce_code95"]["upload_codes"] == ["driver_license"]
    assert _step(shared, "code95")["visible"] is False
    shared_asked = project_required_document_types(_UNCONDITIONAL, shared_facts, employment_id="emp-1")
    assert "driver_license" in shared_asked
    assert "driver_qualification_card" not in shared_asked

    separate, separate_facts = _view(
        {"licence_issuing_country": "BY"},
        base=base,
        requirements=_CE_REQUIREMENTS,
    )
    assert separate["ce_code95"]["evidence_shape"] == "separate"
    assert separate["ce_code95"]["evidence_variant"] == "separate_license_and_code95"
    assert separate["ce_code95"]["upload_codes"] == ["driver_license", "driver_qualification_card"]
    assert _step(separate, "code95")["visible"] is True
    separate_asked = project_required_document_types(_UNCONDITIONAL, separate_facts, employment_id="emp-1")
    assert "driver_license" in separate_asked
    assert "driver_qualification_card" in separate_asked

    blocked, blocked_facts = _view(
        {
            "licence_issuing_country": "PL",
            "licence_categories": ["B"],
            "code95_presence": False,
        },
        base=base,
        today=date(2026, 10, 5),
        requirements=_CE_REQUIREMENTS,
    )
    assert blocked["ce_code95"]["ce"]["resolution"] == "blocking"
    assert blocked["ce_code95"]["code95"]["resolution"] != "blocking"
    assert blocked["ce_code95"]["upload_codes"] == ["driver_license"]
    assert _step(blocked, "code95")["visible"] is False
    blocked_asked = drop_withheld_document_codes(
        ["driver_license", "code95", "tacho_card", "adr"],
        blocked_facts,
        employment_id="emp-1",
        today=date(2026, 10, 5),
    )
    assert "national_identity_card" not in blocked_asked
    assert "driver_license" in blocked_asked

    unrelated = project_required_document_types(
        ["passport", "medical_certificate"],
        shared_facts,
        employment_id="emp-1",
    )
    assert "driver_license" not in unrelated
    assert "medical_certificate" in unrelated
    assert "national_identity_card" not in unrelated
    assert "passport" in unrelated


def test_shared_licence_drops_the_old_qualification_card_blocker() -> None:
    shared = apply_operator_facts_patch(
        empty_facts(),
        {
            "citizenship": "UA",
            "licence_issuing_country": "PL",
            "licence_categories": ["C", "CE"],
        },
        employment_id="emp-1",
    )
    codes = requirement_codes_for_operator(
        ["passport", "driver_license", "driver_qualification_card", "tachograph_card"],
        shared,
    )
    assert "driver_qualification_card" not in codes
    assert codes == ["passport", "driver_license", "tachograph_card"]

    separate = apply_operator_facts_patch(
        empty_facts(),
        {"citizenship": "UA", "licence_issuing_country": "BY"},
        employment_id="emp-1",
    )
    separate_codes = requirement_codes_for_operator(
        ["passport", "driver_license", "driver_qualification_card"],
        separate,
    )
    assert "driver_qualification_card" in separate_codes
    assert "driver_license" in separate_codes
    assert "passport" in separate_codes


def test_answered_card_medical_and_psych_ask_for_those_files() -> None:
    facts = apply_operator_facts_patch(
        empty_facts(),
        {
            "citizenship": "UA",
            "stay_basis": "karta_pobytu",
            "medical_presence": True,
            "psych_presence": True,
        },
        employment_id="emp-1",
    )
    asked = project_required_document_types(
        ["passport", "driver_license", "tachograph_card"],
        facts,
        employment_id="emp-1",
    )
    assert "residence_card" in asked
    assert "decision" in asked
    assert "medical_certificate" in asked
    assert "psychological_certificate" in asked
    assert "passport" in asked

    unanswered = apply_operator_facts_patch(
        empty_facts(),
        {"citizenship": "UA", "stay_basis": "visa_d"},
        employment_id="emp-1",
    )
    visa_asked = project_required_document_types(
        ["passport"],
        unanswered,
        employment_id="emp-1",
    )
    assert "decision" not in visa_asked
    assert "residence_card" not in visa_asked
    assert "medical_certificate" not in visa_asked
    assert "psychological_certificate" not in visa_asked


def test_approved_candidate_evidence_removes_the_resolved_file() -> None:
    base = apply_operator_facts_patch(empty_facts(), {"citizenship": "PL"}, employment_id="emp-1")
    facts = apply_operator_facts_patch(
        base,
        {"licence_issuing_country": "PL", "licence_categories": ["CE"]},
        employment_id="emp-1",
    )
    evidence = [
        {
            "requirement_code": "ce",
            "evidence_variant_code": "combined_eu_license",
            "status": "approved",
            "document_ids": ["doc-1"],
        },
        {
            "requirement_code": "code95",
            "evidence_variant_code": "combined_eu_license",
            "status": "approved",
            "document_ids": ["doc-1"],
        },
    ]
    asked = project_required_document_types(
        ["driver_license", "code95", "visa"],
        facts,
        evidence=evidence,
    )
    assert "driver_license" not in asked
    assert "driver_qualification_card" not in asked
    assert "visa" in asked
