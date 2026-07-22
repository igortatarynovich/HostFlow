"""Regression: invite FK target must resolve on the same SQLAlchemy Base."""

from __future__ import annotations

import importlib
import sys


def test_lead_questionnaire_invite_fk_resolves_tenant_lead_forms() -> None:
    # Prefer the app.models path used under uvicorn /app mount.
    for name in list(sys.modules):
        if name.endswith(".models.lead_questionnaire_invite") or name.endswith(
            ".models.tenant_lead_form"
        ):
            sys.modules.pop(name, None)

    invite_mod = importlib.import_module("app.models.lead_questionnaire_invite")
    form_mod = importlib.import_module("app.models.tenant_lead_form")

    invite_table = invite_mod.LeadQuestionnaireInvite.__table__
    form_table = form_mod.TenantLeadForm.__table__

    assert invite_table.metadata is form_table.metadata
    assert "tenant_lead_forms" in invite_table.metadata.tables
    target_names = {fk.target_fullname for fk in invite_table.foreign_keys}
    assert "tenant_lead_forms.id" in target_names
