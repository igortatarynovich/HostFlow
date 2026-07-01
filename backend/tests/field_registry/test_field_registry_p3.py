"""Field Registry P3 — CandidateProfile bridge for effective candidate card layout."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.field_registry.candidate_layout_bridge import (
    merge_candidate_profile_field_configs,
    resolve_effective_candidate_card_layout,
)
from backend.app.field_registry.constants import DEFAULT_CANDIDATE_LAYOUT_CODE
from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults
from backend.app.models.candidate_profile import CandidateProfile


def test_p3_merge_candidate_profile_overlays_visibility_and_required() -> None:
    layout = {
        "entity_type": "candidate",
        "resolution_source": "platform_layout",
        "sections": [],
        "fields": [
            {
                "qualified_code": "recruitment.candidate.contacts.email",
                "legacy_aliases": ["email"],
                "section_code": "basic",
                "sort_order": 20,
                "visible": True,
                "required": False,
                "name": "Email",
            },
            {
                "qualified_code": "recruitment.candidate.first_name",
                "legacy_aliases": ["first_name"],
                "section_code": "basic",
                "sort_order": 10,
                "visible": True,
                "required": True,
                "name": "First name",
            },
        ],
    }
    profile = CandidateProfile(
        id="profile-bridge-1",
        tenant_id="tenant-1",
        code="custom_driver",
        name="Custom driver",
        config={
            "field_configs": [
                {
                    "field_key": "email",
                    "field_type": "email",
                    "visible": False,
                    "required": True,
                    "order": 1,
                    "label": "Work email",
                }
            ]
        },
    )
    merged = merge_candidate_profile_field_configs(layout, profile)
    email = next(row for row in merged["fields"] if row["qualified_code"].endswith(".email"))
    assert email["visible"] is False
    assert email["required"] is True
    assert email["label_override"] == "Work email"
    assert merged["candidate_profile_code"] == "custom_driver"
    assert merged["resolution_source"].endswith("+candidate_profile")


def test_p3_merge_skips_driver_ce_default_empty_config() -> None:
    layout = {"fields": [{"qualified_code": "recruitment.candidate.first_name", "visible": True}], "sections": []}
    profile = CandidateProfile(
        id="profile-default",
        tenant_id="tenant-1",
        code="driver_ce_default",
        name="Default",
        config={"field_configs": []},
    )
    merged = merge_candidate_profile_field_configs(layout, profile)
    assert merged == layout


@pytest.mark.anyio
async def test_p3_candidate_layout_bridge_resolves_with_profile_id(db) -> None:
    tenant_id = f"fr-p3-{uuid.uuid4().hex[:10]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_card_layout_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    profile = CandidateProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code=f"profile_{uuid.uuid4().hex[:6]}",
        name="Bridge profile",
        config={
            "field_configs": [
                {
                    "field_key": "phone",
                    "field_type": "phone",
                    "visible": True,
                    "required": True,
                    "order": 1,
                }
            ]
        },
    )
    db.add(profile)
    await db.commit()

    layout = await resolve_effective_candidate_card_layout(
        db,
        tenant_id=tenant_id,
        candidate_profile_id=profile.id,
        layout_code=DEFAULT_CANDIDATE_LAYOUT_CODE,
    )
    assert layout["resolution_source"] != "not_found"
    assert layout.get("candidate_profile_id") == profile.id
    phone = next(
        (row for row in layout["fields"] if row["qualified_code"] == "recruitment.candidate.contacts.phone"),
        None,
    )
    assert phone is not None
    assert phone["required"] is True
