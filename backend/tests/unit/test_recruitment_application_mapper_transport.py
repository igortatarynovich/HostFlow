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
            "application_comments_v1": [{"id": "c1", "text": "Call back", "created_at": "2026-08-20T10:00:00Z"}],
        },
    )
    app = lead_to_recruitment_application(lead)
    assert app.transport_lead_id == str(lead.id)
    assert app.extensions["transport_lead_id"] == str(lead.id)
    assert app.extensions["application_comments_v1"][0]["text"] == "Call back"
