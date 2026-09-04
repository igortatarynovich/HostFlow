"""Marketing Source mapping façade (Acquisition UI Cutover C-5).

Persists ``IntakeSourceProfile.mapping_rules`` — no new mapping engine.
Empty authority is filled from leftover Meta form / tenant mapping (MA-2
read-through), then ingest reads only the authority.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.mapping_applied_stamp import (
    MAPPING_APPLIED_V1_KEY,
    compose_applied_evidence,
    empty_applied_evidence,
)
from backend.app.acquisition.mapping_workspace import (
    coerce_schema_fields,
    set_schema_snapshot,
    workspace_envelope,
)
from backend.app.acquisition.sources_read import compute_destination, compute_mapping_health
from backend.app.acquisition.sources_sample import (
    _bindings_for_profile,
    _mapping_rules_for_source,
    load_source_profile,
    preview_source_sample,
    resolve_meta_form_id,
)
from backend.app.acquisition.submission_routing import ACQUISITION_ROUTING_V1_KEY
from backend.app.field_registry.intake_mapping import enrich_mapping_rules_for_storage
from backend.app.models.lead import Lead


def _coerce_rule(raw: Any) -> Optional[dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    source = raw.get("source")
    if isinstance(source, list):
        source = next((str(x).strip() for x in source if str(x).strip()), "")
    source_s = str(source or "").strip()
    if not source_s:
        return None
    target = str(raw.get("target") or "").strip() or None
    qualified = str(raw.get("qualified_field_code") or "").strip() or None
    action = str(raw.get("action") or "").strip().lower() or None
    if action == "ignore":
        target = None
        qualified = None
    fmt = str(raw.get("format") or "string").strip() or "string"
    out: dict[str, Any] = {"source": source_s, "format": fmt}
    if target:
        out["target"] = target
    if qualified:
        out["qualified_field_code"] = qualified
    if action:
        out["action"] = action
    if "overwrite" in raw:
        out["overwrite"] = bool(raw.get("overwrite"))
    option_map = raw.get("option_map")
    if isinstance(option_map, dict):
        cleaned = {
            str(k).strip(): str(v).strip()
            for k, v in option_map.items()
            if str(k).strip() and str(v).strip()
        }
        if cleaned:
            out["option_map"] = cleaned
    return out


def normalize_rules_for_write(rules: list[Any]) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    for raw in rules or []:
        rule = _coerce_rule(raw)
        if rule is None:
            continue
        action = str(rule.get("action") or "").lower()
        if action != "ignore" and not rule.get("target") and not rule.get("qualified_field_code"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "mapping_rule_incomplete",
                    "message": (
                        f"Rule for {rule.get('source')!r} needs target, "
                        "qualified_field_code, or action=ignore"
                    ),
                },
            )
        accepted.append(rule)
    return enrich_mapping_rules_for_storage(accepted)


async def get_source_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_id: str,
) -> dict[str, Any]:
    profile = await load_source_profile(db, tenant_id=tenant_id, source_id=source_id)
    bindings = await _bindings_for_profile(db, tenant_id=tenant_id, profile_id=str(profile.id))
    meta_form_id = resolve_meta_form_id(profile, bindings)
    effective = await _mapping_rules_for_source(
        db, tenant_id=tenant_id, profile=profile, meta_form_id=meta_form_id
    )
    profile_rules = list(getattr(profile, "mapping_rules", None) or [])
    profile_rules = [r for r in profile_rules if isinstance(r, dict)]
    dest, dest_label = compute_destination(
        route_intent=getattr(profile, "route_intent", None),
        lead_target_type=getattr(profile, "lead_target_type", None),
    )
    health = compute_mapping_health(
        connection_status="connected",
        mapping_rules_count=len(effective),
        last_error_code=None,
    )
    workspace = await workspace_envelope(
        db,
        tenant_id=tenant_id,
        profile=profile,
        mapping_rules=effective,
    )
    applied = await _applied_evidence_for_source(
        db,
        tenant_id=tenant_id,
        source_id=str(profile.id),
        current_rules=effective,
        destinations=list(workspace.get("destinations") or []),
    )
    return {
        "source_id": str(profile.id),
        "provider": str(profile.provider or ""),
        "display_name": str(profile.name or profile.code or profile.id),
        "meta_form_id": meta_form_id,
        "mapping_rules": effective,
        "profile_mapping_rules": profile_rules,
        "rules_source": "profile" if profile_rules or effective else "none",
        "mapping_rules_count": len(effective),
        "mapping_health": health,
        "destination": dest,
        "destination_label": dest_label,
        "route_intent": str(getattr(profile, "route_intent", None) or "") or None,
        **workspace,
        "applied_evidence": applied,
    }


async def _applied_evidence_for_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_id: str,
    current_rules: list[dict[str, Any]],
    destinations: list[dict[str, Any]],
) -> dict[str, Any]:
    sid = str(source_id)
    stamp = Lead.normalized[MAPPING_APPLIED_V1_KEY]
    routing = Lead.normalized[ACQUISITION_ROUTING_V1_KEY]
    stmt = (
        select(Lead)
        .where(
            Lead.tenant_id == str(tenant_id),
            stamp.isnot(None),
            or_(
                stamp["source_id"].as_string() == sid,
                routing["intake_source_profile_id"].as_string() == sid,
            ),
        )
        .order_by(Lead.created_at.desc(), Lead.id.desc())
        .limit(1)
    )
    lead = (await db.execute(stmt)).scalars().first()
    if lead is None:
        return empty_applied_evidence()
    normalized = lead.normalized if isinstance(lead.normalized, dict) else {}
    return compose_applied_evidence(
        lead_id=str(lead.id),
        normalized=normalized,
        current_rules=current_rules,
        destinations=destinations,
    )


async def put_source_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_id: str,
    mapping_rules: list[Any],
    schema_snapshot: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    profile = await load_source_profile(db, tenant_id=tenant_id, source_id=source_id)
    accepted = normalize_rules_for_write(list(mapping_rules or []))
    profile.mapping_rules = accepted
    if schema_snapshot is not None:
        fields = coerce_schema_fields(schema_snapshot)
        set_schema_snapshot(profile, {"fields": fields})
    await db.commit()
    await db.refresh(profile)
    return await get_source_mapping(db, tenant_id=tenant_id, source_id=str(profile.id))


async def preview_source_routing(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_id: str,
    sample_payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Dry-run routing preview — no production entities.

    Combines C-4 normalize preview with destination + unmapped-field gate.
    """
    mapping = await get_source_mapping(db, tenant_id=tenant_id, source_id=source_id)
    preview = await preview_source_sample(
        db,
        tenant_id=tenant_id,
        source_id=source_id,
        sample_payload=sample_payload,
    )
    fields = list(preview.get("fields") or [])
    unmapped = [
        f
        for f in fields
        if str(f.get("status") or "") in {"unmapped", "new"}
        and str(f.get("source") or "").strip()
    ]
    ignored = [
        r
        for r in (mapping.get("mapping_rules") or [])
        if isinstance(r, dict) and str(r.get("action") or "").lower() == "ignore"
    ]
    needs_review = bool(unmapped) or int(mapping.get("mapping_rules_count") or 0) <= 0
    return {
        "source_id": str(source_id),
        "creates_entities": False,
        "destination": mapping.get("destination"),
        "destination_label": mapping.get("destination_label"),
        "route_intent": mapping.get("route_intent"),
        "mapping_health": mapping.get("mapping_health"),
        "mapping_rules_count": mapping.get("mapping_rules_count"),
        "unmapped_fields": [str(f.get("source")) for f in unmapped],
        "ignored_fields": [str(r.get("source")) for r in ignored if r.get("source")],
        "needs_review": needs_review,
        "preview": preview,
        "note": (
            "Unknown/unmapped fields force Needs review — not silently dropped."
            if needs_review
            else "All discovered fields are mapped or ignored."
        ),
    }


__all__ = [
    "get_source_mapping",
    "put_source_mapping",
    "preview_source_routing",
    "normalize_rules_for_write",
]
