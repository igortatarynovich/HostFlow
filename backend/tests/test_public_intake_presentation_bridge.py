"""Presentation bridge must not fall back to driver profile for office forms."""

from __future__ import annotations

import pytest

from backend.app.entity_profile.constants import OFFICE_WORKER_PROFILE_CODE
from backend.app.entity_profile.presentation_write import (
    build_tenant_form_presentation_code,
    upsert_tenant_intake_presentation,
    validate_presentation_fields_for_profile,
)
from backend.app.entity_profile.public_intake_presentation_bridge import (
    resolve_public_session_form_presentation,
)
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.models.intake_routing_enums import IntakeChannel, IntakeProvider, RouteIntent
from backend.app.modules.intake_routing import crud as intake_crud


@pytest.mark.anyio
async def test_resolve_presentation_uses_office_entity_profile_not_driver(db, tenant_id: str):
    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    slug = "office-test-form"
    presentation_code = build_tenant_form_presentation_code(
        entity_profile_code=OFFICE_WORKER_PROFILE_CODE,
        public_slug=slug,
    )
    _, _, profile_view = await validate_presentation_fields_for_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_code=OFFICE_WORKER_PROFILE_CODE,
        fields=[
            {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
            {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
            {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
            {"qualified_code": "recruitment.candidate.contacts.email", "intake_level": "required"},
        ],
    )
    entity_profile_id = str((profile_view.get("profile") or {}).get("id") or "")
    assert entity_profile_id

    await upsert_tenant_intake_presentation(
        db,
        tenant_id=tenant_id,
        entity_profile_id=entity_profile_id,
        presentation_code=presentation_code,
        field_subset=[
            "recruitment.candidate.first_name",
            "recruitment.candidate.last_name",
            "recruitment.candidate.contacts.phone",
            "recruitment.candidate.contacts.email",
        ],
        presentation_overrides={},
    )

    from backend.app.models.own_company import OwnCompany
    from sqlalchemy import select

    own_company_id = (
        await db.execute(
            select(OwnCompany.id).where(OwnCompany.tenant_id == tenant_id).limit(1)
        )
    ).scalar_one()

    intake_profile = await intake_crud.create_profile(
        db,
        tenant_id=tenant_id,
        code=f"public-form-{slug}",
        name="Офис — тест",
        own_company_id=str(own_company_id),
        provider=IntakeProvider.public_intake.value,
        channel=IntakeChannel.direct.value,
        route_intent=RouteIntent.candidate_application.value,
        public_slug=slug,
        form_type="candidate_intake",
        lead_type="candidate",
        lead_target_type="candidate",
        entity_profile_code=OFFICE_WORKER_PROFILE_CODE,
        source="public_intake",
        default_language="pl",
        supported_languages="pl,en,ru",
        is_active=True,
    )
    intake_profile.presentation_code = presentation_code
    await intake_crud.create_binding(
        db,
        tenant_id=tenant_id,
        intake_source_profile_id=str(intake_profile.id),
        provider=IntakeProvider.public_intake.value,
        external_key=f"public_slug:{slug}",
        priority=10,
    )
    await db.commit()

    intake_state = {
        "lead_form": {
            "id": "unused-form-id",
            "title": "Офис — тест",
            "public_slug": slug,
            "entity_profile_code": OFFICE_WORKER_PROFILE_CODE,
            "presentation_code": presentation_code,
        },
        "contacts": {},
        "personal": {},
        "experience": {},
        "agreements": {},
    }

    presentation = await resolve_public_session_form_presentation(
        db,
        tenant_id=tenant_id,
        intake_state=intake_state,
    )
    assert presentation is not None
    assert presentation["entity_profile_code"] == OFFICE_WORKER_PROFILE_CODE
    assert presentation["profile_name"] == "Office Worker Candidate"
    field_codes = {f["qualified_code"] for f in presentation["fields"]}
    assert "recruitment.candidate.experience.years_ce" not in field_codes
