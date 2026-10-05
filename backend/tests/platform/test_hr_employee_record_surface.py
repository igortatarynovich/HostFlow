"""Employee Record routes existing facts. It does not store them."""

from backend.app.services.hr_employee_record_surface import (
    GROUP_ORDER,
    apply_citizenship,
    project_employee_record,
)


def _projected(**overrides):
    payload = {
        "identity": {
            "first_name": "Jan",
            "last_name": "Kowalski",
            "birth_date": "1988-04-12",
            "citizenship": "UA",
        },
        "personal": {"citizenship": "BY", "birth_date": "1988-04-12"},
        "phone": "+48",
        "email": None,
        "legal_stay": {"basis": "karta_pobytu"},
        "work_eligibility": {"basis": "separate_required", "valid_for_this_employment": "no"},
        "legal_pass": False,
        "professional_facts": [
            {
                "key": "driving_licence",
                "label": "Driving licence",
                "applicability": "applicable",
                "resolution": "satisfied",
                "evidence_linked": True,
                "not_applicable": False,
            },
            {
                "key": "code_95",
                "label": "Code 95",
                "applicability": "not_applicable",
                "resolution": None,
                "evidence_linked": False,
                "not_applicable": True,
            },
        ],
        "professional_defined": True,
        "terms": {"position": "Driver CE", "intended_start_date": "2026-10-20"},
        "employer": "SIS Trans",
        "client_name": None,
        "actual_start": None,
        "zus_status": None,
        "next_action": {
            "code": "confirm_legal",
            "focus": "work_eligibility",
            "fact_key": "",
            "title": "Confirm legal eligibility",
            "reason": "The chain for this Employment is not a current pass.",
        },
    }
    payload.update(overrides)
    return project_employee_record(**payload)


def test_groups_follow_the_assigned_hierarchy() -> None:
    groups = _projected()["groups"]
    assert [group["id"] for group in groups] == list(GROUP_ORDER)


def test_citizenship_is_the_person_value_and_legal_does_not_copy_it() -> None:
    projected = _projected()
    citizenship = _row(projected, "dane_osobowe.citizenship")
    assert citizenship["value"] == "BY"
    assert citizenship["actions"] == ["edit"]
    legal_ids = [row["id"] for row in _group(projected, "legalizacja")["rows"]]
    assert "citizenship" not in " ".join(legal_ids)
    assert all(row["value"] != "BY" for row in _group(projected, "legalizacja")["rows"])


def test_citizenship_write_keeps_the_other_person_facts() -> None:
    personal = {"birth_date": "1988-04-12", "pesel": "1"}
    merged = apply_citizenship(personal, " PL ")
    assert merged["citizenship"] == "PL"
    assert merged["birth_date"] == "1988-04-12"
    assert personal["birth_date"] == "1988-04-12"
    assert "citizenship" not in personal


def test_missing_formality_is_not_a_question() -> None:
    formalities = _group(_projected(), "formalnosci")
    assert formalities["rows"] == []
    assert formalities["empty"] == "no_applicable_element"
    assert "A1" not in str(formalities)


def test_open_targets_the_record_row_for_the_next_action() -> None:
    projected = _projected()
    assert projected["current_process"]["target_row_id"] == "legalizacja.stay_basis"


def test_code_95_not_applicable_stays_a_status() -> None:
    row = _row(_projected(), "kwalifikacje.code_95")
    assert row["status"] == "not_applicable"
    assert row["value"] is None


def _group(projected: dict, group_id: str) -> dict:
    return next(group for group in projected["groups"] if group["id"] == group_id)


def _row(projected: dict, row_id: str) -> dict:
    for group in projected["groups"]:
        for row in group["rows"]:
            if row["id"] == row_id:
                return row
    raise AssertionError(row_id)
