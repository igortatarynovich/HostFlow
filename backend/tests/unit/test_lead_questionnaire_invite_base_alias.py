"""Regression: invite FK targets must resolve on the same SQLAlchemy Base."""

from __future__ import annotations

import importlib
import sys


def _clear_invite_related_modules() -> None:
    for name in list(sys.modules):
        if name.endswith(
            (
                ".models.lead_questionnaire_invite",
                ".models.tenant_lead_form",
                ".models.lead",
                ".db.base",
                ".db",
            )
        ) or name in {"app.db.base", "backend.app.db.base", "app.db", "backend.app.db"}:
            sys.modules.pop(name, None)


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


def test_lead_questionnaire_invite_fk_resolves_leads_under_dual_base_paths() -> None:
    """Lead uses absolute backend.app.db.base; invite uses relative app.db.base."""
    _clear_invite_related_modules()

    # Same collapse main.py / app.db.base perform under /app/backend symlink.
    app_db = importlib.import_module("app.db")
    app_db_base = importlib.import_module("app.db.base")
    sys.modules["backend.app.db"] = app_db
    sys.modules["backend.app.db.base"] = app_db_base

    lead_mod = importlib.import_module("app.models.lead")
    invite_mod = importlib.import_module("app.models.lead_questionnaire_invite")

    invite_table = invite_mod.LeadQuestionnaireInvite.__table__
    lead_table = lead_mod.Lead.__table__

    assert invite_table.metadata is lead_table.metadata
    assert "leads" in invite_table.metadata.tables
    target_names = {fk.target_fullname for fk in invite_table.foreign_keys}
    assert "leads.id" in target_names
    for fk in invite_table.foreign_keys:
        if fk.target_fullname == "leads.id":
            # Resolving .column raises NoReferencedTableError when MetaData diverges.
            assert fk.column.table.name == "leads"
