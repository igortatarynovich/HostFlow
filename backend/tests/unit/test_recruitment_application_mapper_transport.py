"""Recruitment ApplicationOut exposes transport Lead id and comments."""

from __future__ import annotations

from backend.app.models import Lead
from backend.app.modules.applications.mappers import lead_to_recruitment_application


def test_recruitment_mapper_sets_transport_lead_id_and_comments() -> None:
    lead = Lead(
        id="11111111-1111-1111-1111-111111111111",
        tenant_id="11111111-1111-1111-1111-111111111111",
        source="meta",
        status="new",
        lead_type="candidate",
        payload={},
        normalized={
            "full_name": "Ada",
            "email": "ada@example.com",
            "field_answers": [{"name": "kategoria", "values": ["C+E"], "label": "Jaką masz kategorię?"}],
            "application_comments_v1": [{"id": "c1", "text": "Call back", "created_at": "2026-08-20T10:00:00Z"}],
        },
    )
    app = lead_to_recruitment_application(lead)
    assert app.transport_lead_id == str(lead.id)
    assert app.extensions["transport_lead_id"] == str(lead.id)
    assert app.extensions["application_comments_v1"][0]["text"] == "Call back"
    assert app.extensions["meta_form_answers"][0]["name"] == "kategoria"


def test_recruitment_mapper_keeps_only_questionnaire_answers() -> None:
    lead = Lead(
        id="11111111-1111-1111-1111-111111111111",
        tenant_id="11111111-1111-1111-1111-111111111111",
        source="meta",
        status="new",
        lead_type="candidate",
        payload={},
        normalized={
            "full_name": "Kudakwashe Tapfumaneyi",
            "email": "kudakwashetapfumaneyi5@gmail.com",
            "phone": "+48503499897",
            "field_answers": [
                {
                    "name": "какой у вас опыт работы водителем c+e в международных перевозках по ес?",
                    "values": ["1–2_года"],
                },
                {"name": "full_name", "values": ["Kudakwashe Tapfumaneyi"]},
                {"name": "phone", "values": ["+48503499897"]},
                {"name": "email", "values": ["kudakwashetapfumaneyi5@gmail.com"]},
                {
                    "name": "inbox_url",
                    "values": ["https://business.facebook.com/latest/28393661780251008"],
                },
                {"name": "campaign_name", "values": ["Leads RU C/CE Driver"]},
            ],
            "additional_answers": [
                {"name": "inbox_url", "values": ["https://business.facebook.com/latest/28393661780251008"]},
            ],
        },
    )
    app = lead_to_recruitment_application(lead)
    names = [row["name"] for row in app.extensions["meta_form_answers"]]
    assert names == ["какой у вас опыт работы водителем c+e в международных перевозках по ес?"]
    assert app.extensions["additional_answers"] == []
    assert app.contact.name == "Kudakwashe Tapfumaneyi"
    assert app.contact.phone == "+48503499897"


def test_recruitment_mapper_projects_call_outcome_on_application() -> None:
    lead = Lead(
        id="11111111-1111-1111-1111-111111111111",
        tenant_id="11111111-1111-1111-1111-111111111111",
        source="meta",
        status="in_progress",
        lead_type="candidate",
        payload={},
        normalized={
            "full_name": "Ada",
            "call_result_v1": {"result": "no_answer", "at": "2026-09-01T10:00:00Z"},
            "call_results_v1": [{"result": "no_answer", "at": "2026-09-01T10:00:00Z"}],
        },
    )
    app = lead_to_recruitment_application(lead)
    assert app.extensions["call_result_v1"]["result"] == "no_answer"
    assert app.extensions["call_results_v1"][0]["result"] == "no_answer"
