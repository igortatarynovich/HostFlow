"""The HR employee record is a projection of owners that already exist."""

from __future__ import annotations

from backend.app.services.hr_employee_record_projection import (
    SECTION_ORDER,
    RecordWriteRejected,
    apply_column_write,
    apply_employment_write,
    apply_person_write,
    project_employee_record,
    write_plan,
)
from backend.app.services.operator_facts_surface import facts_from_personal_data


def _field(record: dict, address: str) -> dict:
    for section in record["sections"]:
        for field in section["fields"]:
            if field["address"] == address:
                return field
    raise AssertionError(address)


def _by_source(employment_id: str = "employment-a") -> dict:
    return {
        "employment_id": employment_id,
        "candidate_id": "candidate-1",
        "employee_id": "employee-1",
        "employments": [
            {"id": "employment-a", "state": "preparing"},
            {"id": "employment-b", "state": "preparing"},
        ],
        "person": {
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "first_name_latin": None,
            "last_name_latin": None,
            "phone": "+375",
            "phone_country_code": "BY",
            "email": "ivan@example.com",
            "languages": ["ru"],
            "display_name": "Ivan Ivanov",
        },
        "personal_data": {
            "citizenship": "BY",
            "birth_date": "1990-01-01",
            "operator_facts": {
                "stay_basis": "karta_pobytu",
                "licence_issuing_country": "BY",
                "licence_categories": ["CE"],
                "code95_presence": True,
                "employments": {
                    "employment-a": {
                        "work_authorization_basis": "separate_required",
                        "procedure_type": "employer_declaration",
                    },
                    "employment-b": {
                        "work_authorization_basis": "separate_required",
                        "procedure_type": "work_permit_a",
                    },
                },
            },
        },
        "employment": {
            "state": "preparing",
            "client_company_id": "client-a",
            "vacancy_id": "vacancy-a",
            "started_on": None,
            "ended_on": None,
            "handoff_at": "2026-10-05T10:00:00+00:00",
            "handoff_by_user_id": "user-1",
            "handoff_id": "handoff-1",
            "candidate_snapshot": {"citizenship": "BY"},
        },
        "requirements": [
            {"definition_key": "legal_stay_confirmation", "applicability": "applicable", "resolution": "satisfied"},
            {"definition_key": "labor_market_access", "applicability": "applicable", "resolution": "satisfied"},
            {"definition_key": "driver_entitlement", "applicability": "applicable", "resolution": "satisfied"},
            {"definition_key": "professional_qualification", "applicability": "applicable", "resolution": "satisfied"},
        ],
        "legal_decision": {"outcome": "blocked", "valid_for_this_employment": "operator_verification"},
        "legal_decisions": [{"id": "legal-1", "outcome": "blocked"}],
        "ready_to_start": {"outcome": "blocked"},
        "ready_decisions": [{"id": "ready-1", "outcome": "blocked"}],
        "terms": None,
        "contract_cards": [],
        "prior_jobs": [{"id": "job-1", "employer_name": "Minsk Trans"}],
        "documents": [
            {"id": "doc-card", "doc_type": "residence_card"},
            {"id": "doc-decision", "doc_type": "temporary_residence_decision"},
            {"id": "doc-declaration", "doc_type": "work_permit"},
            {"id": "doc-licence", "doc_type": "driver_license"},
        ],
        "evidence": [
            {
                "id": "ev-stay",
                "requirement_code": "legal_stay_confirmation",
                "evidence_variant_code": "residence_card_and_decision",
                "status": "approved",
                "document_codes": ["residence_card", "temporary_residence_decision"],
            },
            {
                "id": "ev-work",
                "requirement_code": "labor_market_access",
                "evidence_variant_code": "employer_declaration",
                "status": "approved",
                "document_codes": ["work_permit"],
            },
            {
                "id": "ev-ce",
                "requirement_code": "driver_entitlement",
                "evidence_variant_code": "separate_license_and_code95",
                "status": "approved",
                "document_codes": ["driver_license"],
            },
        ],
        "insurance": None,
        "zus": None,
    }


def test_by_employee_record_reads_the_ten_groups_in_order() -> None:
    record = project_employee_record(_by_source())
    assert [(section["key"], section["label"]) for section in record["sections"]] == list(SECTION_ORDER)
    assert _field(record, "person.citizenship")["value"] == "BY"
    assert _field(record, "stay.basis")["value"] == "karta_pobytu"
    assert _field(record, "work.authorization_basis")["value"] == "separate_required"
    assert _field(record, "work.procedure_type")["value"] == "employer_declaration"
    assert _field(record, "legal.outcome")["value"] == "blocked"
    assert _field(record, "legal.valid_for_this_employment")["value"] == "operator_verification"
    assert _field(record, "requirement.legal_stay_confirmation")["value"]["resolution"] == "satisfied"
    assert _field(record, "requirement.labor_market_access")["value"]["resolution"] == "satisfied"
    assert _field(record, "employment.client")["value"] == "client-a"
    assert _field(record, "qualification.licence_categories")["value"] == ["CE"]
    assert _field(record, "qualification.code95_presence")["value"] is True
    assert _field(record, "requirement.driver_entitlement")["value"]["resolution"] == "satisfied"
    document_types = {row["doc_type"] for row in _field(record, "document.rows")["value"]}
    assert document_types == {
        "residence_card",
        "temporary_residence_decision",
        "work_permit",
        "driver_license",
    }
    assert _field(record, "history.legal_decisions")["value"][0]["outcome"] == "blocked"
    assert _field(record, "history.requirements")["value"][0]["definition_key"] == "legal_stay_confirmation"
    assert _field(record, "insurance.profile")["value"] is None
    assert _field(record, "zus.profile")["value"] is None
    assert _field(record, "person.citizenship")["address"] == "person.citizenship"
    assert "operator_facts" in _field(record, "stay.basis")["storage"]


def test_another_employment_keeps_the_person_and_reads_its_own_work() -> None:
    source = _by_source("employment-b")
    source["employment"] = {**source["employment"], "client_company_id": "client-b", "vacancy_id": "vacancy-b"}
    source["legal_decision"] = {"outcome": "pass", "valid_for_this_employment": "yes"}
    source["requirements"] = [
        {"definition_key": "legal_stay_confirmation", "applicability": "applicable", "resolution": "unresolved"},
    ]
    source["ready_to_start"] = {"outcome": "blocked"}
    record = project_employee_record(source)
    assert _field(record, "person.citizenship")["value"] == "BY"
    assert _field(record, "work.procedure_type")["value"] == "work_permit_a"
    assert _field(record, "employment.client")["value"] == "client-b"
    assert _field(record, "legal.outcome")["value"] == "pass"
    assert _field(record, "requirement.legal_stay_confirmation")["value"]["resolution"] == "unresolved"
    assert record["employment_id"] == "employment-b"


def test_person_write_is_visible_on_the_same_storage_recruitment_reads() -> None:
    personal = _by_source()["personal_data"]
    updated = apply_person_write(
        personal,
        address="person.citizenship",
        value="UA",
        employment_id="employment-a",
    )
    seen_by_recruitment = facts_from_personal_data(updated)
    assert seen_by_recruitment["citizenship"] == "UA"
    assert "hr_citizenship" not in updated
    assert updated["operator_facts"]["employments"]["employment-b"]["procedure_type"] == "work_permit_a"


def test_work_write_changes_only_the_selected_employment() -> None:
    personal = _by_source()["personal_data"]
    updated = apply_person_write(
        personal,
        address="work.authorization_basis",
        value="included_in_stay",
        employment_id="employment-a",
    )
    facts = facts_from_personal_data(updated)
    assert facts["employments"]["employment-a"]["work_authorization_basis"] == "included_in_stay"
    assert facts["employments"]["employment-b"]["work_authorization_basis"] == "separate_required"
    assert facts["employments"]["employment-b"]["procedure_type"] == "work_permit_a"


def test_employment_column_write_does_not_touch_the_other_employment() -> None:
    class Row:
        def __init__(self, client: str) -> None:
            self.client_company_id = client

    first = Row("client-a")
    second = Row("client-b")
    apply_employment_write(first, address="employment.client", value="client-a2")
    assert first.client_company_id == "client-a2"
    assert second.client_company_id == "client-b"


def test_write_plan_uses_the_existing_owner() -> None:
    assert write_plan("person.citizenship") == {"kind": "operator_facts", "patch_key": "citizenship"}
    assert write_plan("employment.client")["kind"] == "employment"
    assert write_plan("employment.terms")["writer"] == "confirm_employment_terms"
    assert write_plan("evidence.status")["writer"] == "approve_evidence"
    assert apply_column_write("person.email", "hr@example.com") == {"email": "hr@example.com"}
    try:
        write_plan("legal.outcome")
    except RecordWriteRejected:
        return
    raise AssertionError("legal outcome is a view")
