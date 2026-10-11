"""Employee Record routes existing facts. It does not store them.

The browser walk is not PASS. Citizenship is the reference pattern.
"""

from datetime import date
from pathlib import Path

from backend.app.services.candidate_workforce_lock import recruitment_holds_returned_case
from backend.app.services.hr_employee_record_surface import (
    GROUP_ORDER,
    apply_citizenship,
    apply_person,
    evidence_coverage,
    end_record_employment,
    project_employee_record,
    project_employment_path,
    project_record_overview,
)
from backend.app.services.requirement_document_data import fact_fields_from_document


class _FlushOnlySession:
    def __init__(self):
        self.flushed = False

    async def flush(self) -> None:
        self.flushed = True


async def test_end_record_employment_ends_relationship_and_keeps_employee_context(monkeypatch) -> None:
    from backend.app.models.hr_employment import Employment
    from backend.app.models.workforce_employee import WorkforceEmployee
    from backend.app.services import hr_employee_record_surface as service

    employee = WorkforceEmployee(id="employee-1", tenant_id="tenant-1", display_name="Jan", status="active", meta={})
    employment = Employment(
        id="employment-1",
        tenant_id="tenant-1",
        employee_id="employee-1",
        state="active",
        started_on=date(2026, 8, 12),
    )
    session = _FlushOnlySession()

    async def get_employee(*_args, **_kwargs):
        return employee

    async def get_employment(*_args, **_kwargs):
        return employment

    monkeypatch.setattr(service.workforce_employee_service, "get_employee", get_employee)
    monkeypatch.setattr(service, "display_employment", get_employment)

    result = await end_record_employment(
        session,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        employee_id="employee-1",
        ended_on=date(2026, 9, 30),
        reason="Koniec umowy",
    )

    assert result["accepted"] is True
    assert employment.state == "ended"
    assert employment.ended_on == date(2026, 9, 30)
    assert employee.status == "terminated"
    assert session.flushed is True


async def test_end_record_employment_rejects_date_before_start(monkeypatch) -> None:
    from backend.app.models.hr_employment import Employment
    from backend.app.models.workforce_employee import WorkforceEmployee
    from backend.app.services import hr_employee_record_surface as service

    employee = WorkforceEmployee(id="employee-1", tenant_id="tenant-1", display_name="Jan", status="active")
    employment = Employment(
        id="employment-1",
        tenant_id="tenant-1",
        employee_id="employee-1",
        state="active",
        started_on=date(2026, 8, 12),
    )

    async def get_employee(*_args, **_kwargs):
        return employee

    async def get_employment(*_args, **_kwargs):
        return employment

    monkeypatch.setattr(service.workforce_employee_service, "get_employee", get_employee)
    monkeypatch.setattr(service, "display_employment", get_employment)

    result = await end_record_employment(
        _FlushOnlySession(),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        employee_id="employee-1",
        ended_on=date(2026, 8, 11),
        reason="Koniec umowy",
    )

    assert result == {"accepted": False, "reason": "END_DATE_BEFORE_START"}
    assert employment.state == "active"


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


def test_evidence_boundary_stays_until_the_browser_walk() -> None:
    flow = Path(__file__).resolve().parents[3] / "docs" / "specs" / "workflows" / "hr-driver-operator-flow.md"
    text = flow.read_text(encoding="utf-8")
    assert "Employee Record does not upload, replace, preview, or delete a document." in text
    assert "One evidence may cover N facts." in text
    assert "`missing` means the fact has no required evidence." in text
    assert "`expired` and `rejected` stay those statuses." in text
    assert "Handoff changes authority over the same document." in text
    assert "Citizenship stays a person fact." in text
    assert "The E2E is not PASS." in text
    assert "This file does not add a further action on the record." in text


def test_surface_e2e_is_not_pass() -> None:
    brief = Path(__file__).resolve().parents[3] / "docs" / "specs" / "tasks" / "employee-record-employment-lifecycle.md"
    current = brief.read_text(encoding="utf-8").split("## History", 1)[0]
    assert "The E2E is not PASS." in current
    assert (
        "One write, one canonical value, multiple projections, "
        "dependent decision invalidation, without synchronization."
    ) in current
    assert "Citizenship is the reference pattern." in current
    assert "A later fact does not open its own architecture." in current


def test_person_write_stays_on_the_existing_owner() -> None:
    personal, columns = apply_person(
        {"citizenship": "BY", "operator_facts": {"stay_basis": "karta_pobytu"}},
        {
            "first_name": "Jan",
            "last_name": "Kowalski",
            "birth_date": "1988-04-12",
            "citizenship": "UA",
            "phone": "+48",
            "email": "jan@example.com",
            "address": {
                "country": "PL",
                "city": "Warszawa",
                "street": "Marszałkowska",
                "house": "1",
                "apt": "4",
                "zip": "00-001",
            },
            "pesel": "88041212345",
            "languages": "pl, uk",
        },
    )
    assert personal["citizenship"] == "UA"
    assert personal["operator_facts"]["stay_basis"] == "karta_pobytu"
    assert personal["address"] == {
        "country": "PL",
        "city": "Warszawa",
        "street": "Marszałkowska",
        "house": "1",
        "apt": "4",
        "zip": "00-001",
    }
    assert not isinstance(personal["address"], str)
    assert columns["first_name"] == "Jan"
    assert columns["languages"] == ["pl", "uk"]
    assert "extra" not in columns


def test_terms_action_names_the_missing_fields() -> None:
    projected = _projected(terms={"position": "Driver CE"}, next_action={
        "code": "confirm_terms",
        "focus": "terms",
        "fact_key": "",
        "title": "Confirm employment terms",
        "reason": "The agreed terms of this Employment are not confirmed.",
    })
    assert projected["current_process"]["missing"] == [
        "planned start",
        "compensation",
        "work system",
        "contract basis",
        "workplace",
    ]


def test_returned_case_does_not_ask_hr_to_keep_verifying() -> None:
    projected = _projected(employee_status="returned_to_recruitment", employment_state="ended")
    action = projected["current_process"]["next_action"]
    assert action["code"] == "returned_to_recruitment"
    assert action["title"] == "Returned to recruitment"
    assert action["reason"] == "Waiting for Recruitment update"
    assert projected["current_process"]["destination"] == "recruitment"
    assert projected["current_process"]["target_row_id"] is None
    assert "Verify" not in action["title"]
    assert recruitment_holds_returned_case("returned_to_recruitment")
    assert recruitment_holds_returned_case("returned")
    assert not recruitment_holds_returned_case("onboarding")
    assert not recruitment_holds_returned_case("terminated")


def test_groups_follow_the_assigned_hierarchy() -> None:
    groups = _projected()["groups"]
    assert [group["id"] for group in groups] == list(GROUP_ORDER)


def test_citizenship_is_the_person_value_and_legal_does_not_copy_it() -> None:
    projected = _projected()
    citizenship = _row(projected, "dane_osobowe.citizenship")
    assert citizenship["value"] == "BY"
    assert citizenship["actions"] == []
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
    assert row["evidence"] == "not_required"


def test_one_document_covers_licence_and_code_95() -> None:
    reading = fact_fields_from_document(
        meta={"license_categories": ["C", "CE"]},
        expire_date=date(2037, 1, 28),
    )
    projected = _projected(
        professional_facts=[
            {
                "key": "driving_licence",
                "label": "Driving licence",
                "applicability": "applicable",
                "resolution": "satisfied",
                "evidence_linked": True,
                "document_status": "approved",
                "categories": reading["categories"],
                "valid_until": reading["valid_until"],
            },
            {
                "key": "code_95",
                "label": "Code 95",
                "applicability": "applicable",
                "resolution": "satisfied",
                "evidence_linked": True,
                "document_status": "approved",
                "categories": reading["categories"],
                "valid_until": reading["valid_until"],
            },
            {
                "key": "tachograph_card",
                "label": "Tachograph card",
                "applicability": "applicable",
                "resolution": "unresolved",
                "evidence_linked": False,
            },
        ]
    )
    licence = _row(projected, "kwalifikacje.driving_licence")
    code = _row(projected, "kwalifikacje.code_95")
    card = _row(projected, "kwalifikacje.tachograph_card")
    assert licence["details"] == code["details"]
    assert licence["details"][0]["value"] == "C, CE"
    assert licence["details"][1]["value"] == "2037-01-28"
    assert licence["evidence"] == "approved"
    assert code["evidence"] == "approved"
    assert card["evidence"] == "missing"
    assert "details" not in card
    assert evidence_coverage(applicability="applicable", linked=True, document_status="uploaded") == "in_progress"


def test_path_marks_existing_readings_and_skips_processes_without_a_task() -> None:
    path = project_employment_path(
        phase="preparing",
        identity_complete=True,
        facts=[
            {"key": "driving_licence", "applicability": "applicable", "resolution": "satisfied"},
            {"key": "medical", "applicability": "applicable", "resolution": "unresolved"},
        ],
        legal_pass=False,
        zus_status=None,
        terms_complete=False,
        ready_status="blocked",
    )
    marks = {step["id"]: step["mark"] for step in path}
    assert marks["handoff"] == "completed"
    assert marks["verification"] == "current"
    assert marks["legal"] == "current"
    assert marks["formalities"] == "not_applicable"
    assert marks["terms"] == "current"
    assert marks["ready"] == "pending"
    assert "bhp" not in marks
    assert "start_documents" not in marks
    overview = project_record_overview(
        phase="preparing",
        citizenship="UA",
        stay_basis="karta_pobytu",
        work_basis="separate_required",
        work_status="pending",
        terms={"contract_basis": "umowa", "duration": "fixed", "fixed_term_end": "2027-12-31"},
        start_on="2026-11-02",
        documents=[{"doc_type": "karta_pobytu", "title": "Karta pobytu", "expires_at": "2027-07-29"}],
        facts=[],
        path=path,
    )
    assert overview["notice"] == "attention"
    assert overview["stay_until"] == "2027-07-29"
    assert overview["attention_count"] == 3


def _group(projected: dict, group_id: str) -> dict:
    return next(group for group in projected["groups"] if group["id"] == group_id)


def _row(projected: dict, row_id: str) -> dict:
    for group in projected["groups"]:
        for row in group["rows"]:
            if row["id"] == row_id:
                return row
    raise AssertionError(row_id)
