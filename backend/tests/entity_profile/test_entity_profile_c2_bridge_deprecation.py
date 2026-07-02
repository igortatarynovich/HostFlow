"""C2 — CandidateProfile.config bridge deprecation."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from backend.app.entity_profile.config_deprecation import (
    deprecated_config_fragments_changed,
    enforce_candidate_profile_config_write,
)
from backend.app.entity_profile.facade import resolve_entity_profile_facade
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.field_registry.candidate_layout_bridge import merge_candidate_profile_field_configs
from backend.app.models.candidate_profile import CandidateProfile


pytestmark = pytest.mark.anyio


def test_deprecated_config_fragments_detects_field_configs_change() -> None:
    previous = {"field_configs": [{"field_key": "first_name"}]}
    updated = {"field_configs": [{"field_key": "first_name"}, {"field_key": "email"}]}
    assert deprecated_config_fragments_changed(previous, updated) == ["field_configs"]
    assert deprecated_config_fragments_changed(previous, previous) == []


@pytest.mark.anyio
async def test_c2_blocks_field_configs_write_for_mapped_profile(db, tenant_id: str) -> None:
    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await enforce_candidate_profile_config_write(
            db,
            tenant_id=tenant_id,
            profile_code="driver_ce_default",
            previous_config={"field_configs": []},
            next_config={"field_configs": [{"field_key": "email", "visible": True}]},
        )
    assert exc.value.status_code == 422
    detail = exc.value.detail
    assert detail["code"] == "candidate_profile_config_deprecated"
    assert "field_configs" in detail["changed_keys"]


@pytest.mark.anyio
async def test_c2_allows_unmapped_profile_with_deprecation_warnings(db, tenant_id: str) -> None:
    warnings = await enforce_candidate_profile_config_write(
        db,
        tenant_id=tenant_id,
        profile_code=f"custom_{uuid.uuid4().hex[:8]}",
        previous_config={},
        next_config={"field_configs": [{"field_key": "email", "visible": True}]},
    )
    assert warnings == ["candidate_profile_config_deprecated:field_configs"]


@pytest.mark.anyio
async def test_c2_facade_mapped_profile_uses_registry_not_legacy_bridge(db, tenant_id: str) -> None:
    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    payload = await resolve_entity_profile_facade(
        db,
        tenant_id=tenant_id,
        candidate_profile_code="driver_ce_default",
        include_presentations=False,
    )
    assert payload["bridge_source"] == "entity_profile_registry"
    assert payload["entity_profile_code"]
    assert "legacy_candidate_profile_fallback" not in (payload.get("warnings") or [])


def test_c2_layout_bridge_marks_deprecated_overlay() -> None:
    layout = {
        "fields": [
            {
                "qualified_code": "recruitment.candidate.first_name",
                "legacy_aliases": ["first_name"],
                "visible": True,
                "required": False,
                "section_code": "general",
            }
        ],
        "sections": [],
        "resolution_source": "registry",
    }
    profile = CandidateProfile(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        code="custom_profile",
        name="Custom",
        config={
            "field_configs": [
                {"field_key": "first_name", "visible": False, "required": True, "label": "Given name"},
            ]
        },
        is_active=True,
        is_system=False,
    )
    merged = merge_candidate_profile_field_configs(layout, profile)
    assert merged["layout_bridge_source"] == "candidate_profile_deprecated_overlay"
    assert merged["fields"][0]["visible"] is False
    assert merged["fields"][0]["required"] is True
