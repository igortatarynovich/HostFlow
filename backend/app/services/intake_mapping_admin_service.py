"""Admin services for intake source field mapping (P9)."""

from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.mapping_leftover_writers import (
    mapping_workspace_path,
    raise_intake_form_mapping_evaluator_retired,
    raise_intake_form_mapping_writes_retired,
)
from backend.app.entity_profile.ingest_runtime import IngestEnvelope, stamp_ingest_envelope_v1
from backend.app.entity_profile.mapping_resolve import resolve_mapping_authority
from backend.app.entity_profile.mapping_validation import MappingValidationResult
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.leads.normalizer import coerce_generic_json_to_meta_normalizer_payload, normalize_meta_payload
from backend.app.services.intake_form_admin_context import _load_lead_form


def _coerce_rules(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]
    return []


async def _intake_source_for_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    public_slug: Optional[str],
) -> Optional[IntakeSourceProfile]:
    from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id

    profile_id = await resolve_public_intake_source_profile_id(
        db,
        tenant_id=str(tenant_id),
        lead_form_id=str(form_id),
        public_slug=public_slug,
    )
    if not profile_id:
        return None
    return await intake_crud.get_profile_by_id(db, tenant_id=str(tenant_id), profile_id=str(profile_id))


async def _mapping_path_for_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> str:
    lead_form = await _load_lead_form(db, tenant_id=str(tenant_id), form_id=str(form_id))
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip() or None
    intake_source = await _intake_source_for_form(
        db,
        tenant_id=str(tenant_id),
        form_id=str(form_id),
        public_slug=public_slug,
    )
    return mapping_workspace_path(str(intake_source.id) if intake_source is not None else None)


def extract_source_fields_from_sample(raw_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Discover provider source field names from a sample payload (Meta/webhook/CSV row)."""
    wrapped = coerce_generic_json_to_meta_normalizer_payload(raw_payload)
    entry = (wrapped.get("entry") or [{}])[0] or {}
    changes = (entry.get("changes") or [{}])[0] or {}
    value = changes.get("value") or wrapped
    field_data = value.get("field_data") or []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in field_data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        values = item.get("values") or []
        sample = str(values[0]) if values else ""
        out.append({"source": name, "sample_value": sample})
    if not out and isinstance(raw_payload, dict):
        for key, val in raw_payload.items():
            name = str(key).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            if isinstance(val, (dict, list)):
                sample = json.dumps(val, ensure_ascii=False, default=str)[:200]
            else:
                sample = str(val)[:200]
            out.append({"source": name, "sample_value": sample})
    return out


async def build_intake_form_mapping_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> dict[str, Any]:
    lead_form = await _load_lead_form(db, tenant_id=str(tenant_id), form_id=str(form_id))
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip() or None
    intake_source = await _intake_source_for_form(
        db,
        tenant_id=str(tenant_id),
        form_id=str(form_id),
        public_slug=public_slug,
    )

    bindings: list[dict[str, Any]] = []
    mapping_rules: list[dict[str, Any]] = []
    provider = "public_intake"
    entity_profile_code: Optional[str] = None

    if intake_source is not None:
        provider = str(intake_source.provider or "public_intake")
        entity_profile_code = str(getattr(intake_source, "entity_profile_code", None) or "").strip() or None
        mapping_rules = _coerce_rules(getattr(intake_source, "mapping_rules", None))
        binding_rows = await intake_crud.list_bindings_for_profile(
            db,
            tenant_id=str(tenant_id),
            profile_id=str(intake_source.id),
        )
        bindings = [
            {
                "id": str(b.id),
                "provider": b.provider,
                "external_key": b.external_key,
                "external_key_secondary": b.external_key_secondary,
                "priority": b.priority,
                "is_active": bool(b.is_active),
            }
            for b in binding_rows
        ]

    return {
        "form_id": str(lead_form.id),
        "public_slug": public_slug,
        "entity_profile_code": entity_profile_code,
        "provider": provider,
        "intake_source_profile_id": str(intake_source.id) if intake_source else None,
        "mapping_rules": mapping_rules,
        "provider_bindings": bindings,
    }


async def save_intake_form_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    mapping_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    del mapping_rules
    mapping_path = await _mapping_path_for_form(db, tenant_id=tenant_id, form_id=form_id)
    raise_intake_form_mapping_writes_retired(mapping_path=mapping_path)


async def preview_intake_form_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    raw_payload: dict[str, Any],
    mapping_rules: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    mapping_path = await _mapping_path_for_form(db, tenant_id=tenant_id, form_id=form_id)
    if mapping_rules is not None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "intake_form_mapping_preview_uses_saved_contract",
                "message": (
                    "Intake mapping preview is a read-only diagnostic over the saved "
                    "Mapping contract. Do not pass mapping_rules; that is a second algorithm."
                ),
                "mapping_path": mapping_path,
            },
        )

    lead_form = await _load_lead_form(db, tenant_id=str(tenant_id), form_id=str(form_id))
    public_slug = str(getattr(lead_form, "public_slug", None) or "").strip() or None
    intake_source = await _intake_source_for_form(
        db,
        tenant_id=str(tenant_id),
        form_id=str(form_id),
        public_slug=public_slug,
    )
    if intake_source is None:
        raise HTTPException(status_code=422, detail="Intake source profile is not bound to this form")

    resolved = await resolve_mapping_authority(
        db,
        tenant_id=str(tenant_id),
        intake_source_profile_id=str(intake_source.id),
        payload=raw_payload,
    )
    accepted = list(resolved.rules)
    validation = MappingValidationResult(accepted_rules=accepted)
    wrapped = coerce_generic_json_to_meta_normalizer_payload(raw_payload)
    normalized = normalize_meta_payload(wrapped, field_mapping=accepted)
    envelope = IngestEnvelope(
        raw_payload=dict(raw_payload),
        normalized_payload=dict(normalized),
        entity_profile_code=str(getattr(intake_source, "entity_profile_code", None) or "").strip() or None,
        route_intent=str(getattr(intake_source, "route_intent", None) or "candidate_application"),
        mapping_result=validation.to_dict(),
        intake_source_profile_id=str(intake_source.id),
        mapping_rules_source=resolved.rules_source,
        bridge_source="intake_source_mapping_preview",
    )
    stamp_ingest_envelope_v1(normalized, envelope)
    return {
        "source_fields": extract_source_fields_from_sample(raw_payload),
        "normalized_payload": normalized,
        "ingest_envelope_v1": envelope.to_dict(),
        "mapping_validation": validation.to_dict(),
        "accepted_rules": accepted,
    }


async def test_intake_form_mapping_ingest(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    raw_payload: dict[str, Any],
    mapping_rules: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    del raw_payload, mapping_rules
    mapping_path = await _mapping_path_for_form(db, tenant_id=tenant_id, form_id=form_id)
    raise_intake_form_mapping_evaluator_retired(mapping_path=mapping_path)
