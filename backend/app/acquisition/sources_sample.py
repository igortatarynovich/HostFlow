"""Marketing Sources sample / field-discovery service (Acquisition UI Cutover C-4).

Thin façade over existing Lead payloads + ``extract_source_fields_from_sample`` +
``normalize_meta_payload``. No production Candidate / Application / Inquiry create.
Discovery state is namespaced under ``publication_config_v1.mapping_discovery_v1``
(policy resolver ignores unknown keys).
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.sources_read import (
    extract_lead_form_id,
    extract_lead_profile_id,
    parse_meta_form_id,
)
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import Lead, MetaLeadFormMapping
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.leads.normalizer import (
    coerce_generic_json_to_meta_normalizer_payload,
    normalize_meta_payload,
)
from backend.app.services.intake_mapping_admin_service import extract_source_fields_from_sample

DISCOVERY_CONFIG_KEY = "mapping_discovery_v1"
CAPTURE_NEXT_TTL = timedelta(hours=24)
MAX_PASTE_BYTES = 200_000
SAMPLE_SOURCE_LEAD = "lead"
SAMPLE_SOURCE_PASTE = "paste"
SAMPLE_SOURCE_CAPTURE_NEXT = "capture_next"
SAMPLE_SOURCE_GRAPH = "graph"
SAMPLE_SOURCE_NONE = "none"

_EMAIL_RE = re.compile(r"(email|e-mail|mail)", re.I)
_PHONE_RE = re.compile(r"(phone|tel|mobile|whatsapp)", re.I)
_NAME_RE = re.compile(r"(^name$|full_?name|first_?name|last_?name|fio|имя|фамилия)", re.I)


@dataclass(frozen=True)
class DiscoveredField:
    source: str
    sample_value_masked: str
    proposed_target: Optional[str]
    status: str  # mapped | unmapped | new

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "sample_value_masked": self.sample_value_masked,
            "proposed_target": self.proposed_target,
            "status": self.status,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _publication_config(profile: IntakeSourceProfile) -> dict[str, Any]:
    return _as_record(getattr(profile, "publication_config_v1", None))


def get_discovery_state(profile: IntakeSourceProfile) -> dict[str, Any]:
    return _as_record(_publication_config(profile).get(DISCOVERY_CONFIG_KEY))


def set_discovery_state(profile: IntakeSourceProfile, discovery: dict[str, Any]) -> None:
    cfg = _publication_config(profile)
    cfg[DISCOVERY_CONFIG_KEY] = dict(discovery)
    profile.publication_config_v1 = cfg


def mask_sample_value(source: str, value: str) -> str:
    raw = str(value or "")
    if not raw:
        return ""
    key = str(source or "")
    if _EMAIL_RE.search(key) or ("@" in raw and "." in raw):
        parts = raw.split("@", 1)
        if len(parts) == 2 and parts[0]:
            local = parts[0]
            keep = local[:1]
            return f"{keep}***@{parts[1]}"
        return "***@***"
    if _PHONE_RE.search(key) or re.fullmatch(r"[\d\s+\-()]{7,}", raw):
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 4:
            return f"***{digits[-2:]}"
        return "***"
    if _NAME_RE.search(key):
        token = raw.strip().split()[0] if raw.strip() else ""
        if not token:
            return "***"
        return f"{token[:1]}***"
    if len(raw) <= 2:
        return "***"
    if len(raw) <= 6:
        return f"{raw[:1]}***"
    return f"{raw[:2]}***{raw[-1:]}"


def mask_payload_for_ui(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied payload with common PII leaf values masked."""

    def _walk(node: Any, parent_key: str = "") -> Any:
        if isinstance(node, dict):
            return {str(k): _walk(v, str(k)) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(v, parent_key) for v in node]
        if isinstance(node, str):
            return mask_sample_value(parent_key, node)
        return node

    return _walk(deepcopy(payload))


def _rules_target_index(rules: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        source = str(rule.get("source") or rule.get("from") or "").strip()
        target = str(
            rule.get("target")
            or rule.get("to")
            or rule.get("qualified_code")
            or rule.get("field")
            or ""
        ).strip()
        if source and target:
            out[source.lower()] = target
    return out


def _coerce_rules(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict) and isinstance(raw.get("rules"), list):
        raw = raw.get("rules")
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, dict)]


def build_discovered_fields(
    *,
    raw_payload: dict[str, Any],
    mapping_rules: list[dict[str, Any]],
    previous_field_names: Optional[set[str]] = None,
) -> list[DiscoveredField]:
    extracted = extract_source_fields_from_sample(raw_payload)
    targets = _rules_target_index(mapping_rules)
    prev = previous_field_names or set()
    fields: list[DiscoveredField] = []
    for item in extracted:
        source = str(item.get("source") or "").strip()
        if not source:
            continue
        sample = str(item.get("sample_value") or "")
        proposed = targets.get(source.lower())
        if proposed:
            status_s = "mapped"
        elif prev and source.lower() not in prev:
            status_s = "new"
        else:
            status_s = "unmapped"
        fields.append(
            DiscoveredField(
                source=source,
                sample_value_masked=mask_sample_value(source, sample),
                proposed_target=proposed,
                status=status_s,
            )
        )
    return fields


async def load_source_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_id: str,
) -> IntakeSourceProfile:
    profile = await intake_crud.get_profile_by_id(
        db, tenant_id=str(tenant_id), profile_id=str(source_id)
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return profile


async def _bindings_for_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_id: str,
) -> list[IntakeSourceBinding]:
    return await intake_crud.list_bindings_for_profile(
        db, tenant_id=str(tenant_id), profile_id=str(profile_id)
    )


def resolve_meta_form_id(
    profile: IntakeSourceProfile,
    bindings: list[IntakeSourceBinding],
) -> Optional[str]:
    for b in bindings:
        if str(b.provider).lower() == "meta" or str(profile.provider or "").lower() == "meta":
            fid = parse_meta_form_id(b.external_key)
            if fid:
                return fid
    code = str(profile.code or "")
    if code.startswith("meta-form-"):
        return code[len("meta-form-") :] or None
    return None


async def _mapping_rules_for_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile: IntakeSourceProfile,
    meta_form_id: Optional[str],
) -> list[dict[str, Any]]:
    from backend.app.entity_profile.mapping_resolve import resolve_mapping_authority

    resolved = await resolve_mapping_authority(
        db,
        tenant_id=str(tenant_id),
        intake_source_profile_id=str(profile.id),
        form_id=meta_form_id,
        source=str(getattr(profile, "provider", None) or "meta"),
    )
    if resolved.migrated:
        await db.refresh(profile)
    return list(resolved.rules)


async def _latest_lead_for_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_id: str,
    meta_form_id: Optional[str],
    created_after: Optional[datetime] = None,
) -> Optional[Lead]:
    tid = str(tenant_id)
    form_id_to_profile: dict[str, str] = {}
    if meta_form_id:
        form_id_to_profile[str(meta_form_id)] = str(profile_id)
        mm = (
            await db.execute(
                select(MetaLeadFormMapping).where(
                    MetaLeadFormMapping.tenant_id == tid,
                    MetaLeadFormMapping.form_id == str(meta_form_id),
                )
            )
        ).scalar_one_or_none()
        if mm and mm.last_sample_lead_id:
            lead = await db.get(Lead, str(mm.last_sample_lead_id))
            if lead is not None and str(lead.tenant_id) == tid:
                if created_after is None or (
                    lead.created_at is not None and lead.created_at >= created_after
                ):
                    return lead

    stmt = (
        select(Lead)
        .where(Lead.tenant_id == tid)
        .order_by(desc(Lead.created_at))
        .limit(80)
    )
    if created_after is not None:
        stmt = stmt.where(Lead.created_at >= created_after)
    rows = list((await db.execute(stmt)).scalars().all())
    for lead in rows:
        form_id = extract_lead_form_id(normalized=lead.normalized, payload=lead.payload)
        pid = extract_lead_profile_id(
            normalized=lead.normalized,
            form_id=form_id,
            form_id_to_profile=form_id_to_profile,
        )
        if pid == str(profile_id):
            return lead
        if meta_form_id and form_id and str(form_id) == str(meta_form_id):
            return lead
    return None


def _parse_iso(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _validate_paste_payload(sample_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(sample_payload, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_sample_payload", "message": "sample_payload must be an object"},
        )
    try:
        encoded = json.dumps(sample_payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_sample_payload", "message": "sample_payload is not JSON-serializable"},
        ) from exc
    if len(encoded.encode("utf-8")) > MAX_PASTE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "sample_payload_too_large",
                "message": f"sample_payload exceeds {MAX_PASTE_BYTES} bytes",
            },
        )
    return dict(sample_payload)


def _sample_response(
    *,
    source_id: str,
    sample_source: str,
    raw_payload: Optional[dict[str, Any]],
    mapping_rules: list[dict[str, Any]],
    lead_id: Optional[str],
    captured_at: Optional[str],
    capture_next_until: Optional[str],
    previous_field_names: Optional[set[str]] = None,
) -> dict[str, Any]:
    payload = raw_payload if isinstance(raw_payload, dict) else {}
    fields = (
        build_discovered_fields(
            raw_payload=payload,
            mapping_rules=mapping_rules,
            previous_field_names=previous_field_names,
        )
        if payload
        else []
    )
    return {
        "source_id": str(source_id),
        "sample_source": sample_source,
        "lead_id": lead_id,
        "captured_at": captured_at,
        "capture_next_until": capture_next_until,
        "has_sample": bool(payload),
        "fields": [f.as_dict() for f in fields],
        "raw_payload_masked": mask_payload_for_ui(payload) if payload else {},
        "mapping_rules_count": len(mapping_rules),
    }


def _previous_field_names(discovery: dict[str, Any]) -> set[str]:
    return {str(x).lower() for x in (discovery.get("previous_field_names") or []) if str(x).strip()}


def _field_names_from_payload(payload: dict[str, Any]) -> set[str]:
    return {
        str(f.get("source") or "").lower()
        for f in extract_source_fields_from_sample(payload)
        if str(f.get("source") or "").strip()
    }


def persist_sample_on_profile(
    profile: IntakeSourceProfile,
    *,
    payload: dict[str, Any],
    sample_source: str,
    lead_id: Optional[str],
    captured_at: Optional[str],
    keep_capture_window: bool = True,
) -> None:
    discovery = get_discovery_state(profile)
    previous = _previous_field_names(discovery)
    next_state: dict[str, Any] = {
        "sample_payload": dict(payload),
        "sample_source": sample_source,
        "sample_lead_id": lead_id,
        "sample_captured_at": captured_at or _now().isoformat(),
        "previous_field_names": sorted(previous | _field_names_from_payload(payload)),
    }
    if keep_capture_window:
        until = discovery.get("capture_next_until")
        armed = discovery.get("capture_next_armed_at")
        if until:
            next_state["capture_next_until"] = until
        if armed:
            next_state["capture_next_armed_at"] = armed
    set_discovery_state(profile, next_state)


async def _try_graph_latest_payload(
    db: AsyncSession,
    *,
    tenant_id: str,
    bindings: list[IntakeSourceBinding],
    meta_form_id: Optional[str],
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Pull Graph latest ``field_data``. Never mints a Facebook test lead."""
    form_id = str(meta_form_id or "").strip()
    if not form_id:
        return None, None
    from backend.app.acquisition.campaign_source_cards import parse_meta_page_id
    from backend.app.modules.leads.admin_service import get_page_access_token
    from backend.app.modules.leads.meta_marketing_graph import fetch_leadgen_form_latest_lead

    page_id: Optional[str] = None
    for binding in bindings:
        page_id = parse_meta_page_id(getattr(binding, "external_key_secondary", "") or "")
        if page_id:
            break
    if not page_id:
        return None, "no_page_token"
    token = await get_page_access_token(db, tenant_id, page_id)
    if not token:
        return None, "no_page_token"
    try:
        latest = await fetch_leadgen_form_latest_lead(form_id, token)
    except Exception as exc:
        return None, f"graph_error:{exc}"[:180]
    if not isinstance(latest, dict):
        return None, "no_graph_lead"
    field_data = latest.get("field_data")
    if not isinstance(field_data, list):
        field_data = []
    return (
        {
            "id": latest.get("id"),
            "form_id": latest.get("form_id") or form_id,
            "created_time": latest.get("created_time"),
            "field_data": field_data,
        },
        None,
    )


async def resolve_sample_for_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile: IntakeSourceProfile,
    meta_form_id: Optional[str],
    mapping_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    """Discovery, then latest HostFlow lead. Graph pull is an explicit refresh."""
    discovery = get_discovery_state(profile)
    previous = _previous_field_names(discovery)

    capture_until = _parse_iso(discovery.get("capture_next_until"))
    if capture_until is not None and capture_until > _now():
        armed_at = _parse_iso(discovery.get("capture_next_armed_at")) or (
            capture_until - CAPTURE_NEXT_TTL
        )
        lead = await _latest_lead_for_source(
            db,
            tenant_id=tenant_id,
            profile_id=str(profile.id),
            meta_form_id=meta_form_id,
            created_after=armed_at,
        )
        if lead is not None and isinstance(lead.payload, dict):
            persist_sample_on_profile(
                profile,
                payload=dict(lead.payload),
                sample_source=SAMPLE_SOURCE_CAPTURE_NEXT,
                lead_id=str(lead.id),
                captured_at=_now().isoformat(),
                keep_capture_window=False,
            )
            await db.commit()
            await db.refresh(profile)
            discovery = get_discovery_state(profile)
            previous = _previous_field_names(discovery)

    stored_payload = discovery.get("sample_payload")
    if isinstance(stored_payload, dict) and stored_payload:
        return _sample_response(
            source_id=str(profile.id),
            sample_source=str(discovery.get("sample_source") or SAMPLE_SOURCE_PASTE),
            raw_payload=stored_payload,
            mapping_rules=mapping_rules,
            lead_id=str(discovery["sample_lead_id"]) if discovery.get("sample_lead_id") else None,
            captured_at=str(discovery.get("sample_captured_at") or "") or None,
            capture_next_until=str(discovery.get("capture_next_until") or "") or None,
            previous_field_names=previous,
        )

    lead = await _latest_lead_for_source(
        db,
        tenant_id=tenant_id,
        profile_id=str(profile.id),
        meta_form_id=meta_form_id,
    )
    if lead is not None and isinstance(lead.payload, dict):
        return _sample_response(
            source_id=str(profile.id),
            sample_source=SAMPLE_SOURCE_LEAD,
            raw_payload=dict(lead.payload),
            mapping_rules=mapping_rules,
            lead_id=str(lead.id),
            captured_at=lead.created_at.isoformat() if lead.created_at else None,
            capture_next_until=str(discovery.get("capture_next_until") or "") or None,
            previous_field_names=previous,
        )

    return _sample_response(
        source_id=str(profile.id),
        sample_source=SAMPLE_SOURCE_NONE,
        raw_payload=None,
        mapping_rules=mapping_rules,
        lead_id=None,
        captured_at=None,
        capture_next_until=str(discovery.get("capture_next_until") or "") or None,
        previous_field_names=previous,
    )


async def get_source_sample(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_id: str,
) -> dict[str, Any]:
    profile = await load_source_profile(db, tenant_id=tenant_id, source_id=source_id)
    bindings = await _bindings_for_profile(db, tenant_id=tenant_id, profile_id=str(profile.id))
    meta_form_id = resolve_meta_form_id(profile, bindings)
    mapping_rules = await _mapping_rules_for_source(
        db, tenant_id=tenant_id, profile=profile, meta_form_id=meta_form_id
    )
    return await resolve_sample_for_profile(
        db,
        tenant_id=tenant_id,
        profile=profile,
        meta_form_id=meta_form_id,
        mapping_rules=mapping_rules,
    )


async def persist_latest_sample(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_id: str,
) -> dict[str, Any]:
    """Store Graph latest ``field_data`` or the latest HostFlow lead as mapping evidence."""
    profile = await load_source_profile(db, tenant_id=tenant_id, source_id=source_id)
    bindings = await _bindings_for_profile(db, tenant_id=tenant_id, profile_id=str(profile.id))
    meta_form_id = resolve_meta_form_id(profile, bindings)
    graph_payload, graph_error = await _try_graph_latest_payload(
        db, tenant_id=tenant_id, bindings=bindings, meta_form_id=meta_form_id
    )
    if graph_payload:
        captured = str(graph_payload.get("created_time") or "").strip() or _now().isoformat()
        lead_id = str(graph_payload.get("id") or "").strip() or None
        persist_sample_on_profile(
            profile,
            payload=graph_payload,
            sample_source=SAMPLE_SOURCE_GRAPH,
            lead_id=lead_id,
            captured_at=captured,
        )
        await db.commit()
        await db.refresh(profile)
        return {"persisted": True, "source": SAMPLE_SOURCE_GRAPH, "error": None}

    lead = await _latest_lead_for_source(
        db,
        tenant_id=tenant_id,
        profile_id=str(profile.id),
        meta_form_id=meta_form_id,
    )
    if lead is not None and isinstance(lead.payload, dict) and lead.payload:
        persist_sample_on_profile(
            profile,
            payload=dict(lead.payload),
            sample_source=SAMPLE_SOURCE_LEAD,
            lead_id=str(lead.id),
            captured_at=lead.created_at.isoformat() if lead.created_at else _now().isoformat(),
        )
        await db.commit()
        await db.refresh(profile)
        return {"persisted": True, "source": SAMPLE_SOURCE_LEAD, "error": graph_error}

    return {"persisted": False, "source": SAMPLE_SOURCE_NONE, "error": graph_error or "no_sample"}


async def store_sample_from_payload(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_id: str,
    sample_payload: dict[str, Any],
) -> dict[str, Any]:
    profile = await load_source_profile(db, tenant_id=tenant_id, source_id=source_id)
    payload = _validate_paste_payload(sample_payload)
    bindings = await _bindings_for_profile(db, tenant_id=tenant_id, profile_id=str(profile.id))
    meta_form_id = resolve_meta_form_id(profile, bindings)
    mapping_rules = await _mapping_rules_for_source(
        db, tenant_id=tenant_id, profile=profile, meta_form_id=meta_form_id
    )
    discovery = get_discovery_state(profile)
    previous = {str(x).lower() for x in (discovery.get("previous_field_names") or []) if str(x).strip()}
    field_names = {
        str(f.get("source") or "").lower()
        for f in extract_source_fields_from_sample(payload)
        if str(f.get("source") or "").strip()
    }
    captured_at = _now().isoformat()
    set_discovery_state(
        profile,
        {
            "sample_payload": payload,
            "sample_source": SAMPLE_SOURCE_PASTE,
            "sample_lead_id": None,
            "sample_captured_at": captured_at,
            "previous_field_names": sorted(previous | field_names),
        },
    )
    await db.commit()
    return _sample_response(
        source_id=str(profile.id),
        sample_source=SAMPLE_SOURCE_PASTE,
        raw_payload=payload,
        mapping_rules=mapping_rules,
        lead_id=None,
        captured_at=captured_at,
        capture_next_until=None,
        previous_field_names=previous,
    )


async def arm_capture_next(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_id: str,
) -> dict[str, Any]:
    profile = await load_source_profile(db, tenant_id=tenant_id, source_id=source_id)
    discovery = get_discovery_state(profile)
    armed_at = _now()
    until = armed_at + CAPTURE_NEXT_TTL
    discovery["capture_next_armed_at"] = armed_at.isoformat()
    discovery["capture_next_until"] = until.isoformat()
    # Keep any existing sample until a new lead arrives.
    set_discovery_state(profile, discovery)
    await db.commit()
    return {
        "source_id": str(profile.id),
        "capture_next_armed_at": armed_at.isoformat(),
        "capture_next_until": until.isoformat(),
        "message": "Next matching submission for this Source will seed the mapping sample (lazy capture on sample GET).",
    }


async def preview_source_sample(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_id: str,
    sample_payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Dry-run normalize. Never creates Candidate / Application / Inquiry / Lead."""
    profile = await load_source_profile(db, tenant_id=tenant_id, source_id=source_id)
    bindings = await _bindings_for_profile(db, tenant_id=tenant_id, profile_id=str(profile.id))
    meta_form_id = resolve_meta_form_id(profile, bindings)
    mapping_rules = await _mapping_rules_for_source(
        db, tenant_id=tenant_id, profile=profile, meta_form_id=meta_form_id
    )

    payload: Optional[dict[str, Any]] = None
    if sample_payload is not None:
        payload = _validate_paste_payload(sample_payload)
    else:
        discovery = get_discovery_state(profile)
        stored = discovery.get("sample_payload")
        if isinstance(stored, dict) and stored:
            payload = dict(stored)
        else:
            lead = await _latest_lead_for_source(
                db,
                tenant_id=tenant_id,
                profile_id=str(profile.id),
                meta_form_id=meta_form_id,
            )
            if lead is not None and isinstance(lead.payload, dict):
                payload = dict(lead.payload)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "sample_required",
                "message": "No sample payload available. Paste a payload, arm capture-next, or wait for a lead.",
            },
        )

    wrapped = coerce_generic_json_to_meta_normalizer_payload(payload)
    normalized = normalize_meta_payload(wrapped, field_mapping=mapping_rules)
    fields = build_discovered_fields(raw_payload=payload, mapping_rules=mapping_rules)
    return {
        "source_id": str(profile.id),
        "fields": [f.as_dict() for f in fields],
        "normalized_payload": normalized,
        "raw_payload_masked": mask_payload_for_ui(payload),
        "mapping_rules_count": len(mapping_rules),
        "accepted_rules": mapping_rules,
        "creates_entities": False,
    }


__all__ = [
    "CAPTURE_NEXT_TTL",
    "DISCOVERY_CONFIG_KEY",
    "MAX_PASTE_BYTES",
    "arm_capture_next",
    "build_discovered_fields",
    "get_discovery_state",
    "get_source_sample",
    "mask_payload_for_ui",
    "mask_sample_value",
    "persist_latest_sample",
    "preview_source_sample",
    "resolve_sample_for_profile",
    "set_discovery_state",
    "store_sample_from_payload",
]
