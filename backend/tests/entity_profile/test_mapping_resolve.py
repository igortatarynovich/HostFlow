"""MA-2: ingest consults exactly one mapping store."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from backend.app.models.own_company import OwnCompany
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.leads import crud, normalizer
from backend.app.entity_profile.mapping_resolve import resolve_mapping_authority
from backend.app.modules.leads.field_mapping_resolve import resolve_field_mapping_for_ingest
from backend.app.reference.mapping_authority import RULES_SOURCE_AUTHORITY


def _meta_payload(*, form_id: str, page_id: str, phone: str) -> dict:
    return {
        "entry": [
            {
                "id": page_id,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": str(uuid.uuid4().int)[:15],
                            "form_id": form_id,
                            "page_id": page_id,
                            "field_data": [
                                {"name": "phone_number", "values": [phone]},
                            ],
                        },
                    }
                ],
            }
        ]
    }


async def _make_profile(db, *, tenant_id: str, form_id: str, page_id: str = ""):
    oc = OwnCompany(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=f"MA2 OC {uuid.uuid4().hex[:6]}",
    )
    db.add(oc)
    await db.flush()
    profile = await intake_crud.create_profile(
        db,
        tenant_id=tenant_id,
        code=f"meta-form-{form_id}",
        name=f"Meta form {form_id}",
        own_company_id=oc.id,
        provider="meta",
        channel="paid",
        route_intent="candidate_application",
    )
    await intake_crud.create_binding(
        db,
        tenant_id=tenant_id,
        intake_source_profile_id=profile.id,
        provider="meta",
        external_key=f"form_id:{form_id}",
        external_key_secondary=f"page_id:{page_id}" if page_id else "",
    )
    return profile


@pytest.mark.anyio
async def test_authority_wins_over_leftover_stores(db, tenant_id: str) -> None:
    form_id = f"form-{uuid.uuid4().hex[:8]}"
    page_id = "259905353877064"
    profile = await _make_profile(db, tenant_id=tenant_id, form_id=form_id, page_id=page_id)
    profile.mapping_rules = [{"source": "phone_number", "target": "phone", "format": "phone"}]
    await db.execute(
        sa.text(
            """
            INSERT INTO meta_lead_settings (tenant_id, auto_create_enabled, mask_pii_in_logs, field_mapping)
            VALUES (:t, true, true, CAST(:m AS jsonb))
            ON CONFLICT (tenant_id) DO UPDATE SET field_mapping = CAST(:m AS jsonb)
            """
        ),
        {"t": tenant_id, "m": '[{"source": "email", "target": "email", "format": "email"}]'},
    )
    await crud.upsert_meta_form_mapping(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        page_id=page_id,
        mapping_rules=[{"source": "full_name", "target": "full_name", "format": "string"}],
    )
    await db.commit()

    payload = _meta_payload(form_id=form_id, page_id=page_id, phone="+48111222333")
    resolved = await resolve_mapping_authority(
        db, tenant_id=tenant_id, payload=payload, intake_source_profile_id=str(profile.id)
    )
    assert resolved.rules_source == RULES_SOURCE_AUTHORITY
    assert any(r.get("target") == "phone" for r in resolved.rules)
    assert not any(r.get("target") == "email" for r in resolved.rules)
    assert not any(r.get("target") == "full_name" for r in resolved.rules)
    assert resolved.migrated is False


@pytest.mark.anyio
async def test_empty_authority_migrates_leftover_form_rules(db, tenant_id: str) -> None:
    form_id = f"form-{uuid.uuid4().hex[:8]}"
    page_id = "484113398123847"
    profile = await _make_profile(db, tenant_id=tenant_id, form_id=form_id, page_id=page_id)
    await crud.upsert_meta_form_mapping(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        page_id=page_id,
        mapping_rules=[{"source": "custom_q", "target": "vacancy_hint", "format": "string"}],
    )
    await db.commit()

    payload = _meta_payload(form_id=form_id, page_id=page_id, phone="+48123456789")
    resolved = await resolve_mapping_authority(
        db, tenant_id=tenant_id, payload=payload, intake_source_profile_id=str(profile.id)
    )
    assert resolved.migrated is True
    assert resolved.rules_source == RULES_SOURCE_AUTHORITY
    assert any(r.get("target") == "vacancy_hint" for r in resolved.rules)

    await db.refresh(profile)
    stored = [r for r in (profile.mapping_rules or []) if isinstance(r, dict)]
    assert any(r.get("target") == "vacancy_hint" for r in stored)

    again = await resolve_mapping_authority(
        db, tenant_id=tenant_id, payload=payload, intake_source_profile_id=str(profile.id)
    )
    assert again.migrated is False
    assert any(r.get("target") == "vacancy_hint" for r in again.rules)


@pytest.mark.anyio
async def test_no_profile_does_not_answer_from_leftover(db, tenant_id: str) -> None:
    form_id = f"form-{uuid.uuid4().hex[:8]}"
    page_id = "259905353877066"
    await db.execute(
        sa.text(
            """
            INSERT INTO meta_lead_settings (tenant_id, auto_create_enabled, mask_pii_in_logs, field_mapping)
            VALUES (:t, true, true, CAST(:m AS jsonb))
            ON CONFLICT (tenant_id) DO UPDATE SET field_mapping = CAST(:m AS jsonb)
            """
        ),
        {"t": tenant_id, "m": '[{"source": "email", "target": "email", "format": "email"}]'},
    )
    await crud.upsert_meta_form_mapping(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        page_id=page_id,
        mapping_rules=[{"source": "phone_number", "target": "phone", "format": "phone"}],
    )
    await db.commit()

    payload = _meta_payload(form_id=form_id, page_id=page_id, phone="+48999888777")
    rules = await resolve_field_mapping_for_ingest(db, tenant_id=tenant_id, payload=payload)
    assert rules == []
    normalized = normalizer.normalize_meta_payload(payload, field_mapping=rules)
    assert normalized.get("email") in (None, "")
