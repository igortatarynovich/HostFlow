from __future__ import annotations

from types import SimpleNamespace

from backend.app.services.hr_recruitment_transfer import flatten_recruitment_candidate_fields, merge_flat_into_handoff_candidate


def _candidate(**kwargs):
    extra = kwargs.pop("extra", {})
    personal = kwargs.pop("personal_data", {})
    contacts = kwargs.pop("contacts", {})
    return SimpleNamespace(
        _get_extra=lambda: extra,
        _get_personal_data=lambda: personal,
        _get_contacts=lambda: contacts,
        **kwargs,
    )


def test_flatten_recruitment_candidate_fields_address_and_contacts() -> None:
    cand = _candidate(
        first_name="Jan",
        last_name="Kowalski",
        email="jan@example.com",
        phone="+48111222333",
        phone_country_code="+48",
        extra={
            "citizenship": "UA",
            "work_country": "PL",
            "country_code": "UA",
            "address": {
                "country": "PL",
                "city": "Warsaw",
                "street": "Marszałkowska",
                "house": "10",
                "zip": "00-001",
            },
        },
    )
    flat = flatten_recruitment_candidate_fields(cand)  # type: ignore[arg-type]
    assert flat["full_name"] == "Jan Kowalski"
    assert flat["phone_country_code"] == "+48"
    assert flat["country_code"] == "UA"
    assert flat["work_country"] == "PL"
    assert flat["address_country"] == "PL"
    assert flat["city"] == "Warsaw"


def test_merge_flat_into_handoff_candidate_namespace() -> None:
    ns = merge_flat_into_handoff_candidate(
        {"candidate": {"citizenship": "UA"}},
        {"city": "Warsaw", "phone_country_code": "+48"},
    )
    assert ns["candidate"]["city"] == "Warsaw"
    assert ns["candidate"]["phone_country_code"] == "+48"
    assert ns["candidate"]["citizenship"] == "UA"
