"""Field Registry P5 — vacancy layout binding + intake qualified field mapping."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.field_registry.constants import DEFAULT_VACANCY_LAYOUT_CODE
from backend.app.field_registry.intake_mapping import (
    enrich_mapping_rule_for_storage,
    legacy_normalized_target_from_qualified,
    qualified_code_from_legacy_target,
    resolve_intake_mapping_target,
)
from backend.app.field_registry.resolver import resolve_effective_card_layout
from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults
from backend.app.modules.leads.schemas import MetaLeadFieldMappingRule


def test_p5_intake_qualified_resolves_to_normalized_phone() -> None:
    rule = {
        "source": "phone_number",
        "qualified_field_code": "recruitment.candidate.contacts.phone",
        "format": "phone",
    }
    assert resolve_intake_mapping_target(rule) == "phone"


def test_p5_intake_legacy_target_still_resolves() -> None:
    rule = {"source": "email", "target": "email", "format": "email"}
    assert resolve_intake_mapping_target(rule) == "email"


def test_p5_enrich_mapping_rule_fills_legacy_target_from_qualified() -> None:
    enriched = enrich_mapping_rule_for_storage(
        {"source": "phone_number", "qualified_field_code": "recruitment.candidate.contacts.phone"}
    )
    assert enriched["target"] == "phone"
    assert enriched["qualified_field_code"] == "recruitment.candidate.contacts.phone"


def test_p5_enrich_mapping_rule_accepts_legacy_from_to_aliases() -> None:
    """Older Meta admin rows stored {from, to}; GET settings must not 500."""
    enriched = enrich_mapping_rule_for_storage({"from": "phone_number", "to": "phone"})
    assert enriched["source"] == "phone_number"
    assert enriched["target"] == "phone"
    rule = MetaLeadFieldMappingRule.model_validate({"from": "full_name", "to": "full_name"})
    assert rule.source == "full_name"
    assert rule.target == "full_name"


def test_p5_enrich_mapping_rule_infers_qualified_from_legacy_target() -> None:
    enriched = enrich_mapping_rule_for_storage({"source": "email", "target": "email"})
    assert enriched["qualified_field_code"] == "recruitment.candidate.contacts.email"


def test_p5_meta_lead_mapping_rule_model_coerces_qualified() -> None:
    rule = MetaLeadFieldMappingRule.model_validate(
        {
            "source": "phone_number",
            "qualified_field_code": "recruitment.candidate.contacts.phone",
            "format": "phone",
        }
    )
    assert rule.target == "phone"
    assert rule.qualified_field_code == "recruitment.candidate.contacts.phone"


def test_p5_legacy_normalized_helpers_round_trip() -> None:
    code = "platform.identity.address"
    legacy = legacy_normalized_target_from_qualified(code)
    assert legacy == "address"
    assert qualified_code_from_legacy_target(legacy) == code


@pytest.mark.anyio
async def test_p5_vacancy_effective_layout_has_canonical_fields(db) -> None:
    tenant_id = f"fr-p5-{uuid.uuid4().hex[:10]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_card_layout_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()

    layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type="vacancy",
        layout_code=DEFAULT_VACANCY_LAYOUT_CODE,
        module="recruitment",
    )
    assert layout["resolution_source"] != "not_found"
    codes = {row["qualified_code"] for row in layout["fields"]}
    assert "recruitment.vacancy.title" in codes
    assert "recruitment.vacancy.description" in codes
