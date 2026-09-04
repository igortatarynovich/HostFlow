"""Per-form Meta field mapping resolves through the MA-2 authority store."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.models.own_company import OwnCompany
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.leads import normalizer
from backend.app.modules.leads.field_mapping_resolve import resolve_field_mapping_for_ingest


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


async def _profile(db, *, tenant_id: str, form_id: str, page_id: str, rules: list[dict]):
    oc = OwnCompany(id=str(uuid.uuid4()), tenant_id=tenant_id, name=f"Meta OC {uuid.uuid4().hex[:6]}")
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
    profile.mapping_rules = rules
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
async def test_resolve_field_mapping_uses_authority_not_tenant(tenant_id: str) -> None:
    form_id = f"form-{uuid.uuid4().hex[:8]}"
    page_id = "259905353877064"
    async with async_session_maker() as db:
        await _profile(
            db,
            tenant_id=tenant_id,
            form_id=form_id,
            page_id=page_id,
            rules=[{"source": "phone_number", "target": "phone", "format": "phone"}],
        )
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
        await db.commit()

        payload = _meta_payload(form_id=form_id, page_id=page_id, phone="+48111222333")
        rules = await resolve_field_mapping_for_ingest(db, tenant_id=tenant_id, payload=payload)
        assert any(r.get("target") == "phone" for r in rules)
        assert not any(r.get("target") == "email" for r in rules)

        other_form = _meta_payload(form_id="other-form", page_id=page_id, phone="+48111222334")
        fallback = await resolve_field_mapping_for_ingest(db, tenant_id=tenant_id, payload=other_form)
        assert fallback == []


@pytest.mark.anyio
async def test_normalize_uses_authority_rules(tenant_id: str) -> None:
    form_id = f"form-{uuid.uuid4().hex[:8]}"
    page_id = "484113398123847"
    async with async_session_maker() as db:
        await _profile(
            db,
            tenant_id=tenant_id,
            form_id=form_id,
            page_id=page_id,
            rules=[{"source": "custom_q", "target": "vacancy_hint", "format": "string"}],
        )
        await db.commit()
        payload = _meta_payload(form_id=form_id, page_id=page_id, phone="+48123456789")
        payload["entry"][0]["changes"][0]["value"]["field_data"].append(
            {"name": "custom_q", "values": ["vac-uuid-hint"]}
        )
        rules = await resolve_field_mapping_for_ingest(db, tenant_id=tenant_id, payload=payload)
        normalized = normalizer.normalize_meta_payload(payload, field_mapping=rules)
        assert normalized.get("vacancy_hint") == "vac-uuid-hint"


@pytest.mark.anyio
async def test_normalize_uses_qualified_field_code_target(tenant_id: str) -> None:
    form_id = f"form-{uuid.uuid4().hex[:8]}"
    page_id = "259905353877065"
    phone = "+48999888777"
    async with async_session_maker() as db:
        await _profile(
            db,
            tenant_id=tenant_id,
            form_id=form_id,
            page_id=page_id,
            rules=[
                {
                    "source": "phone_number",
                    "qualified_field_code": "recruitment.candidate.contacts.phone",
                    "format": "phone",
                },
            ],
        )
        await db.commit()
        payload = _meta_payload(form_id=form_id, page_id=page_id, phone=phone)
        rules = await resolve_field_mapping_for_ingest(db, tenant_id=tenant_id, payload=payload)
        assert any(
            r.get("qualified_field_code") == "recruitment.candidate.contacts.phone" for r in rules
        )
        normalized = normalizer.normalize_meta_payload(payload, field_mapping=rules)
        assert normalized.get("phone") == phone
