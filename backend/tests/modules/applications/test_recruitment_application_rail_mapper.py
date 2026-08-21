"""Mapper projection for recruitment application rail (RODO, stage, comments)."""

from __future__ import annotations

from backend.app.models import Lead
from backend.app.modules.applications.mappers import lead_to_recruitment_application


def test_recruitment_application_mapper_exposes_rodo_stage_comments() -> None:
    lead = Lead(
        id="11111111-1111-1111-1111-111111111111",
        tenant_id="11111111-1111-1111-1111-111111111111",
        source="meta",
        status="new",
        stage="new",
        lead_type="candidate",
        payload={},
        normalized={
            "full_name": "Rail Applicant",
            "email": "rail@example.com",
            "rodo": {"status": "manual_required"},
            "application_comments_v1": [{"note": "Call back", "at": "2026-08-20T10:00:00Z"}],
        },
    )
    app = lead_to_recruitment_application(lead)
    assert app.extensions["stage"] == "new"
    assert app.extensions["rodo"]["satisfied"] is False
    assert app.extensions["rodo"]["status"] == "manual_required"
    assert app.extensions["comments"][0]["note"] == "Call back"


def test_recruitment_application_mapper_source_provided_satisfies_rodo() -> None:
    lead = Lead(
        id="22222222-2222-2222-2222-222222222222",
        tenant_id="11111111-1111-1111-1111-111111111111",
        source="meta",
        status="new",
        stage="contacted",
        lead_type="candidate",
        payload={},
        normalized={"rodo": {"status": "source_provided"}},
    )
    app = lead_to_recruitment_application(lead)
    assert app.extensions["rodo"]["satisfied"] is True
    assert app.extensions["rodo"]["status"] == "source_provided"
    assert app.extensions["stage"] == "contacted"
