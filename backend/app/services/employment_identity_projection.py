"""Canonical employment identity — derived read-model from verified fields only (PR5)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.app.models.workforce_hr_verified_field import (
    FIELD_STATUS_APPROVE_OK,
    FIELD_STATUS_CONFLICT,
    FIELD_STATUS_PENDING,
)

PROJECTION_STATUS_COMPLETE = "complete"
PROJECTION_STATUS_INCOMPLETE = "incomplete"
PROJECTION_STATUS_CONFLICTED = "conflicted"
PROJECTION_STATUS_STALE = "stale"

# Downstream-ready minimum (derived only; not the same as critical-field approve gate).
REQUIRED_IDENTITY_ATTRS: frozenset[str] = frozenset(
    {
        "legal_name",
        "citizenship",
    }
)

# Optional attrs that expire — past date marks projection stale.
EXPIRY_ATTRS: frozenset[str] = frozenset(
    {
        "permit_expiry",
        "medical_expiry",
        "psychotests_expiry",
        "code95_expiry",
    }
)

# attr -> list of {field_code, source_document_keys?}
_IDENTITY_SOURCES: dict[str, list[dict[str, Any]]] = {
    "legal_name": [{"field_code": "full_name"}],
    "citizenship": [{"field_code": "citizenship"}],
    "pesel": [{"field_code": "pesel"}],
    "permit_type": [{"field_code": "permit_type"}],
    "permit_expiry": [
        {"field_code": "document_expiry", "source_document_keys": ["Work permit", "Legal stay"]},
    ],
    "residence_basis": [
        {"field_code": "permit_type", "source_document_keys": ["Legal stay", "Work permit"]},
        {"field_code": "work_country"},
    ],
    "medical_expiry": [
        {"field_code": "exam_valid_until", "source_document_keys": ["Medical"]},
    ],
    "psychotests_expiry": [
        {"field_code": "exam_valid_until", "source_document_keys": ["Psychological"]},
    ],
    # Placeholders until verified-field catalog grows (PR6+).
    "birth_date": [{"field_code": "birth_date"}],
    "passport_number": [{"field_code": "passport_number"}],
    "driver_license_categories": [{"field_code": "driver_license_categories"}],
    "code95_expiry": [{"field_code": "code95_expiry"}],
}

_IDENTITY_LABELS: dict[str, str] = {
    "legal_name": "Legal name",
    "birth_date": "Date of birth",
    "citizenship": "Citizenship",
    "pesel": "PESEL / national ID",
    "passport_number": "Passport number",
    "residence_basis": "Residence / work basis",
    "permit_type": "Permit type",
    "permit_expiry": "Permit / stay expiry",
    "driver_license_categories": "Driver license categories",
    "code95_expiry": "Code 95 expiry",
    "medical_expiry": "Medical exam expiry",
    "psychotests_expiry": "Psychological exam expiry",
}


def _parse_date(value: str) -> Optional[date]:
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw[:10] if fmt == "%Y-%m-%d" else raw, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _field_matches_source(field: dict[str, Any], rule: dict[str, Any]) -> bool:
    if str(field.get("field_code") or "") != str(rule.get("field_code") or ""):
        return False
    keys = rule.get("source_document_keys")
    if not keys:
        return True
    doc_key = str(field.get("source_document_key") or "")
    return doc_key in keys


def _pick_source_field(
    verified_fields: list[dict[str, Any]], rules: list[dict[str, Any]]
) -> Optional[dict[str, Any]]:
    for rule in rules:
        code = str(rule.get("field_code") or "")
        candidates = [f for f in verified_fields if _field_matches_source(f, rule)]
        if not candidates:
            continue
        # Prefer verified/overridden with value; skip pure pending.
        for f in candidates:
            if str(f.get("status") or "") in FIELD_STATUS_APPROVE_OK and f.get("verified_value"):
                return f
        for f in candidates:
            if str(f.get("status") or "") == FIELD_STATUS_CONFLICT:
                return f
        for f in candidates:
            if str(f.get("status") or "") == FIELD_STATUS_PENDING:
                return f
        return candidates[0]
    return None


def _attribute_provenance(field: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not field:
        return None
    return {
        "field_code": field.get("field_code"),
        "source_document_id": field.get("source_document_id"),
        "source_document_key": field.get("source_document_key"),
        "document_verification_id": field.get("document_verification_id"),
        "field_status": field.get("status"),
        "verified_by_user_id": field.get("verified_by_user_id"),
        "verified_at": field.get("verified_at"),
        "override_reason": field.get("override_reason"),
        "conflict_reason": field.get("conflict_reason"),
    }


def build_employment_identity_projection(
    verified_fields: list[dict[str, Any]],
    *,
    derived_at: Optional[datetime] = None,
) -> dict[str, Any]:
    """Build derived employment identity from verified fields SoT (read-only projection)."""
    now = derived_at or datetime.now(timezone.utc)
    attributes: dict[str, Optional[str]] = {}
    attribute_meta: dict[str, Any] = {}
    conflicts: list[str] = []
    missing_required: list[str] = []
    pending_sources: list[str] = []

    for attr, rules in _IDENTITY_SOURCES.items():
        source = _pick_source_field(verified_fields, rules)
        meta = _attribute_provenance(source)
        attribute_meta[attr] = meta

        st = str(source.get("status") or "") if source else ""
        val = str(source.get("verified_value") or "").strip() if source and st in FIELD_STATUS_APPROVE_OK else None
        if st == FIELD_STATUS_CONFLICT and source:
            conflicts.append(attr)
            val = str(source.get("verified_value") or "").strip() or None
        elif st == FIELD_STATUS_PENDING and source:
            pending_sources.append(attr)

        attributes[attr] = val or None

    for req in sorted(REQUIRED_IDENTITY_ATTRS):
        if not attributes.get(req):
            missing_required.append(req)

    for attr in conflicts:
        if attr not in missing_required:
            pass

    # Overall status
    if conflicts:
        status = PROJECTION_STATUS_CONFLICTED
    elif missing_required:
        status = PROJECTION_STATUS_INCOMPLETE
    else:
        status = PROJECTION_STATUS_COMPLETE
        for exp_attr in EXPIRY_ATTRS:
            exp_val = attributes.get(exp_attr)
            if not exp_val:
                continue
            exp_date = _parse_date(exp_val)
            if exp_date and exp_date < now.date():
                status = PROJECTION_STATUS_STALE
                break

    if status == PROJECTION_STATUS_COMPLETE and pending_sources:
        # Partial optional attrs still pending — keep complete if required satisfied.
        pass

    if status == PROJECTION_STATUS_INCOMPLETE and any(attributes.values()) and not conflicts:
        # Partial identity built; required still missing.
        pass

    filled = sum(1 for v in attributes.values() if v)
    total = len(_IDENTITY_SOURCES)

    return {
        "status": status,
        "derived_at": now.isoformat(),
        "attributes": attributes,
        "attribute_labels": dict(_IDENTITY_LABELS),
        "attribute_meta": attribute_meta,
        "missing_required": missing_required,
        "conflicts": conflicts,
        "pending_attributes": pending_sources,
        "filled_count": filled,
        "total_count": total,
        "ready_for_downstream": status in (PROJECTION_STATUS_COMPLETE, PROJECTION_STATUS_STALE),
    }
