"""Regression: B2B contact_person email + no circular import on preview path."""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.services.communication_deliveries.questionnaire_email import (
    lead_contact_email,
    lead_contact_name,
)


def test_lead_contact_email_reads_b2b_contact_person() -> None:
    lead = SimpleNamespace(
        normalized={
            "contact_person": {
                "full_name": "Anna Kowalska",
                "email": "anna@client.test",
            }
        },
        payload={},
    )
    assert lead_contact_email(lead) == "anna@client.test"  # type: ignore[arg-type]
    assert lead_contact_name(lead) == "Anna Kowalska"  # type: ignore[arg-type]


def test_lead_contact_email_falls_back_to_top_level() -> None:
    lead = SimpleNamespace(
        normalized={"email": "top@example.test", "full_name": "Top"},
        payload={},
    )
    assert lead_contact_email(lead) == "top@example.test"  # type: ignore[arg-type]


def test_questionnaire_email_module_imports_without_circular_error() -> None:
    """Fresh import must not raise ImportError (circular send_communication ↔ inbound)."""
    import importlib
    import sys

    # Drop modules that participate in the previous cycle so we re-enter cold.
    for name in list(sys.modules):
        if name.startswith("backend.app.services.communication_deliveries") or name in {
            "backend.app.communications.send_communication",
            "backend.app.communications.inbound_resolve",
            "backend.app.communications.inbound_ingest",
            "backend.app.communications.execute_intent",
            "backend.app.communications.prepare_send",
            "backend.app.api.v1.communications",
            "backend.app.api.v1.communications.routes.ingest",
        }:
            sys.modules.pop(name, None)

    mod = importlib.import_module(
        "backend.app.services.communication_deliveries.questionnaire_email"
    )
    assert callable(mod.compose_questionnaire_invite_email)
    assert callable(mod.send_questionnaire_invite_email)
