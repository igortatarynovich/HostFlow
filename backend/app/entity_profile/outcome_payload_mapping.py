"""Canonical normalized payload → derivative entity fields (P5B)."""

from __future__ import annotations

from typing import Any, Optional


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _trim_or_none(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def map_normalized_to_client_company_create(
    normalized: dict[str, Any],
    *,
    lead_payload: Optional[dict[str, Any]] = None,
    source_channel: str,
    lead_id: str,
) -> dict[str, Any]:
    """Map intake normalized payload to ``CompanyCreate``-compatible kwargs."""
    payload = lead_payload or {}
    company_profile = _record(normalized.get("company_profile")) or _record(payload.get("company"))
    contact_person = _record(normalized.get("contact_person")) or _record(payload.get("contact"))
    need = _record(normalized.get("need")) or _record(payload.get("need"))
    marketing = _record(normalized.get("marketing"))
    meta = _record(normalized.get("meta"))

    company_name = (
        _trim_or_none(company_profile.get("name"))
        or _trim_or_none(normalized.get("company_name"))
        or _trim_or_none(payload.get("company_name"))
        or _trim_or_none(normalized.get("full_name"))
    )
    if not company_name:
        raise ValueError("company_name_required")

    primary_contact = {
        "full_name": _trim_or_none(contact_person.get("full_name")) or _trim_or_none(normalized.get("full_name")),
        "role": _trim_or_none(contact_person.get("role")),
        "email": _trim_or_none(contact_person.get("email")) or _trim_or_none(normalized.get("email")),
        "phone": _trim_or_none(contact_person.get("phone")) or _trim_or_none(normalized.get("phone")),
        "whatsapp": bool(contact_person.get("whatsapp")) if contact_person.get("whatsapp") is not None else None,
        "source": "client_lead",
        "source_lead_id": str(lead_id),
    }
    primary_contact = {k: v for k, v in primary_contact.items() if v is not None and v != ""}
    contacts_payload: dict[str, Any] = {}
    if primary_contact:
        contacts_payload = {"primary": primary_contact}

    return {
        "name": company_name,
        "legal_name": _trim_or_none(company_profile.get("legal_name")) or company_name,
        "tax_id": _trim_or_none(company_profile.get("tax_id"))
        or _trim_or_none(company_profile.get("nip"))
        or _trim_or_none(company_profile.get("vat")),
        "phone": _trim_or_none(contact_person.get("phone")) or _trim_or_none(normalized.get("phone")),
        "email": _trim_or_none(contact_person.get("email")) or _trim_or_none(normalized.get("email")),
        "website": _trim_or_none(company_profile.get("website")),
        "country_code": _trim_or_none(company_profile.get("country_code")),
        "country": _trim_or_none(company_profile.get("country")),
        "city": _trim_or_none(company_profile.get("city")),
        "address": _trim_or_none(company_profile.get("address")),
        "company_role": "client",
        "party_business_roles": "service_client",
        "client_stage": "lead_converted",
        "client_source": _trim_or_none(source_channel),
        "contacts": contacts_payload or None,
        "extra": {
            "company_role": "client",
            "company_kind": "client",
            "source": source_channel,
            "source_lead_id": str(lead_id),
            "source_profile": meta.get("source_profile"),
            "intake": {
                "company_profile": company_profile,
                "contact_person": contact_person,
                "need": need,
                "marketing": marketing,
                "meta": meta,
            },
            "needs": [need] if need else [],
        },
    }


def map_normalized_to_service_order_create(
    normalized: dict[str, Any],
    *,
    lead: Any,
    source_channel: str,
) -> dict[str, Any]:
    """Map intake normalized payload to ``AdditionalServicesService.create_order`` payload."""
    company_id = _trim_or_none(getattr(lead, "company_id", None))
    if not company_id:
        raise ValueError("lead_company_required")

    contact_bits = [
        _trim_or_none(normalized.get("full_name")) or "",
        _trim_or_none(normalized.get("email")) or "",
        _trim_or_none(normalized.get("phone")) or "",
    ]
    note_lines = [
        "Created from intake lead",
        f"Lead ID: {getattr(lead, 'id', '')}",
        f"Source channel: {source_channel}",
    ]
    compact_contact = " · ".join(value for value in contact_bits if value)
    if compact_contact:
        note_lines.append(f"Contact: {compact_contact}")

    service_code = _trim_or_none(normalized.get("service_code")) or _trim_or_none(
        _record(normalized.get("need")).get("service_code")
    )
    audit: dict[str, Any] = {
        "source": "lead_outcome_executor",
        "lead_id": str(getattr(lead, "id", "")),
        "lead_status": getattr(lead, "status", None),
        "lead_stage": getattr(lead, "stage", None),
        "source_channel": source_channel,
    }
    if service_code:
        audit["service_code"] = service_code

    return {
        "company_id": company_id,
        "currency": _trim_or_none(normalized.get("currency")) or "PLN",
        "notes": "\n".join(note_lines),
        "requested_by": "system",
        "audit": audit,
    }
