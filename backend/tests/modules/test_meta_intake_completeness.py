"""Meta Intake Completeness — contract: no form answer dropped; B2B naming."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from backend.app.modules.applications.mappers import lead_to_sales_inquiry
from backend.app.modules.leads import normalizer
from backend.app.modules.leads.normalizer import resolve_b2b_inquiry_company_name
from backend.app.modules.leads.service._bulk import _merge_lead_normalized_fallback

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "meta" / "full_leadgen_webhook.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_full_meta_fixture_no_field_answer_dropped():
    payload = _load_fixture()
    value = payload["entry"][0]["changes"][0]["value"]
    field_data = value["field_data"]
    assert field_data, "fixture must include field_data"

    data = normalizer.normalize_meta_payload(payload)

    assert "field_answers" in data
    answer_names = [row["name"] for row in data["field_answers"]]
    for item in field_data:
        assert item["name"] in answer_names

    # Unknown / custom questions retained as additional_answers (never dropped).
    additional_names = {row["name"] for row in data["additional_answers"]}
    assert "ile_osob_potrzebujesz?" in additional_names
    assert "kiedy_start?" in additional_names
    assert "dodatkowe_uwagi" in additional_names
    # Structured / aliased fields are not "additional".
    assert "nazwa_firmy" not in additional_names
    assert "full_name" not in additional_names
    assert "email" not in additional_names


def test_b2b_inquiry_company_naming_priority():
    assert (
        resolve_b2b_inquiry_company_name(
            {
                "company_profile": {"name": "Profile Co"},
                "company_name": "Name Co",
                "company_name_hint": "Hint Co",
            },
            lead_company_name="Lead Co",
        )
        == "Profile Co"
    )
    assert (
        resolve_b2b_inquiry_company_name(
            {"company_name": "Name Co", "company_name_hint": "Hint Co"},
            lead_company_name="Lead Co",
        )
        == "Name Co"
    )
    assert (
        resolve_b2b_inquiry_company_name(
            {"company_name_hint": "Hint Co"},
            lead_company_name="Lead Co",
        )
        == "Hint Co"
    )
    assert resolve_b2b_inquiry_company_name({}, lead_company_name="Lead Co") == "Lead Co"
    assert resolve_b2b_inquiry_company_name({"first_name": "Anna"}) == "Компания"


def test_sales_inquiry_projection_surfaces_meta_answers_and_company():
    payload = _load_fixture()
    normalized = normalizer.normalize_meta_payload(payload)
    lead = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        normalized=normalized,
        payload=payload,
        company_name=None,
        source="meta",
        stage="new",
        status="new",
        assigned_to=None,
        recruiter_id=None,
        next_action_type=None,
        updated_at=None,
        created_at=None,
        priority=None,
        converted_client_id=None,
        client_account_id=None,
    )
    app = lead_to_sales_inquiry(lead)
    assert app.title == "Transport Synergia Sp. z o.o."
    answers = app.extensions["meta_form_answers"]
    names = [row["name"] for row in answers]
    assert "dodatkowe_uwagi" in names
    assert "nazwa_firmy" in names
    assert any(row["name"] == "dodatkowe_uwagi" for row in app.extensions["additional_answers"])
    assert app.extensions["raw_payload_stored"] is True


def test_merge_preserves_field_answers_when_re_normalize_empty():
    prior = {
        "field_answers": [{"name": "custom_q", "values": ["yes"]}],
        "additional_answers": [{"name": "custom_q", "values": ["yes"]}],
        "company_name_hint": "Prior Co",
        "company_name": "Prior Co",
        "raw_field_names": ["custom_q"],
    }
    normalized: dict = {"email": "a@example.com"}
    _merge_lead_normalized_fallback(normalized, prior)
    assert normalized["field_answers"][0]["name"] == "custom_q"
    assert normalized["additional_answers"][0]["name"] == "custom_q"
    assert normalized["company_name_hint"] == "Prior Co"
