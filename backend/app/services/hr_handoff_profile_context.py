"""Map immutable handoff snapshot + recruitment candidate data into HR verification profile context (PR11)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot
from backend.app.services.hr_profile_address import coerce_address_dict, promote_address_fields
from backend.app.services.hr_recruitment_transfer import (
    flatten_recruitment_candidate_fields,
    merge_flat_into_handoff_candidate,
)

_DOC_TYPE_ALIASES: dict[str, str] = {
    "driver_license": "driver_license",
    "driver_license_code95": "driver_license",
    "eu_driver_license": "driver_license",
    "code95": "code95",
    "qualification_code95": "code95",
    "driver_license_code95": "code95",
    "tacho_card": "tacho_card",
    "tachograph_card": "tacho_card",
}


def build_handoff_profile_namespace(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten handoff snapshot v1 into paths used by ``_dig(..., 'handoff.*')``."""
    if not isinstance(payload, dict):
        return {}
    cand = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    name = cand.get("name") if isinstance(cand.get("name"), dict) else {}
    contacts = cand.get("contacts") if isinstance(cand.get("contacts"), dict) else {}
    first = str(name.get("first_name") or "").strip()
    last = str(name.get("last_name") or "").strip()
    full = f"{first} {last}".strip() or None
    citizenship = cand.get("citizenship")
    if citizenship is not None:
        citizenship = str(citizenship).strip() or None
    birth_date = cand.get("birth_date")
    if birth_date is not None:
        birth_date = str(birth_date).strip()[:10] or None
    candidate_out: dict[str, Any] = {
        "full_name": full,
        "first_name": first or None,
        "last_name": last or None,
        "citizenship": citizenship,
        "birth_date": birth_date,
        "email": contacts.get("email"),
        "phone": contacts.get("phone"),
        "phone_country_code": contacts.get("phone_country_code") or cand.get("phone_country_code"),
    }
    addr_raw = cand.get("address")
    if isinstance(addr_raw, str) and addr_raw.strip():
        candidate_out["address"] = addr_raw.strip()
    elif isinstance(addr_raw, dict):
        promote_address_fields(candidate_out, addr_raw)
        candidate_out["address"] = addr_raw
    for key in (
        "birth_date",
        "work_country",
        "country_code",
        "phone_country_code",
        "address_country",
        "city",
        "postal_code",
        "address_street",
        "address_house",
        "address_apt",
        "address_line",
        "experience_summary",
        "last_position",
        "experience_eu_years",
    ):
        if cand.get(key) not in (None, ""):
            candidate_out.setdefault(key, cand.get(key))
    return {
        "candidate": candidate_out,
        "application": payload.get("application") if isinstance(payload.get("application"), dict) else None,
        "documents": list(payload.get("documents") or []) if isinstance(payload.get("documents"), list) else [],
    }


def _norm_doc_type(raw: str) -> str:
    return str(raw or "").strip().lower().replace("-", "_")


def merge_recruiter_transport_fields(
    handoff_ns: dict[str, Any],
    *,
    snapshot_payload: dict[str, Any] | None = None,
    candidate_extra: dict[str, Any] | None = None,
    candidate_personal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add driver / Code95 / tacho values from snapshot document list + live candidate recruitment fields."""
    out = dict(handoff_ns) if handoff_ns else {}
    transport: dict[str, Any] = dict(out.get("transport") or {})

    payload = snapshot_payload if isinstance(snapshot_payload, dict) else {}
    for doc in payload.get("documents") or []:
        if not isinstance(doc, dict):
            continue
        bucket = _DOC_TYPE_ALIASES.get(_norm_doc_type(str(doc.get("type") or "")))
        if not bucket:
            continue
        slot = transport.setdefault(bucket, {})
        if doc.get("expires_at"):
            slot["expires_at"] = doc.get("expires_at")

    merged_extra: dict[str, Any] = {}
    if isinstance(candidate_extra, dict):
        merged_extra.update(candidate_extra)
    if isinstance(candidate_personal, dict):
        merged_extra.update(candidate_personal)

    lic_num = merged_extra.get("license_number")
    if lic_num is not None and str(lic_num).strip():
        transport.setdefault("driver_license", {})["number"] = str(lic_num).strip()

    cats = merged_extra.get("license_categories")
    if cats is not None:
        if isinstance(cats, list):
            cats = ", ".join(str(x).strip() for x in cats if str(x).strip())
        else:
            cats = str(cats).strip()
        if cats:
            transport.setdefault("driver_license", {})["categories"] = cats

    for extra_key, bucket, field in (
        ("code95_number", "code95", "number"),
        ("code95_expiry", "code95", "expires_at"),
        ("tacho_card_number", "tacho_card", "number"),
        ("tacho_card_expiry", "tacho_card", "expires_at"),
        ("tachograph_card_number", "tacho_card", "number"),
        ("tachograph_card_expiry", "tacho_card", "expires_at"),
    ):
        val = merged_extra.get(extra_key)
        if val is not None and str(val).strip():
            transport.setdefault(bucket, {})[field] = str(val).strip()

    out["transport"] = transport
    return out


async def _load_live_candidate_fields(
    db: AsyncSession,
    candidate_id: Optional[str],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    """Live recruitment candidate extra/personal + flat snapshot fields for HR verification."""
    cid = str(candidate_id or "").strip()
    if not cid:
        return None, None, {}
    from backend.app.models.candidate import Candidate

    cand = await db.get(Candidate, cid)
    if not cand:
        return None, None, {}
    extra = cand._get_extra()
    personal = cand._get_personal_data()
    flat: dict[str, Any] = flatten_recruitment_candidate_fields(cand)
    contacts_data = getattr(cand, "contacts", None)
    if isinstance(contacts_data, dict):
        if contacts_data.get("email") and not flat.get("email"):
            flat["email"] = contacts_data.get("email")
        if contacts_data.get("phone") and not flat.get("phone"):
            flat["phone"] = contacts_data.get("phone")
        if contacts_data.get("phone_country_code") and not flat.get("phone_country_code"):
            flat["phone_country_code"] = contacts_data.get("phone_country_code")
    profile = extra.get("profile") if isinstance(extra.get("profile"), dict) else {}
    if profile.get("experience"):
        flat.setdefault("experience_summary", profile.get("experience"))
    if extra.get("experience_eu_years") is not None:
        flat.setdefault("experience_eu_years", extra.get("experience_eu_years"))
    for k in (
        "birth_date",
        "pesel",
        "national_id",
        "work_country",
        "passport_number",
        "passport_series",
        "passport_issue_date",
        "passport_expiry",
        "passport_valid_to",
    ):
        if extra.get(k):
            flat.setdefault(k, extra.get(k))
        if personal.get(k):
            flat.setdefault(k, flat.get(k) or personal.get(k))
    if getattr(cand, "birth_date", None):
        flat.setdefault("birth_date", str(cand.birth_date)[:10])
    elif personal.get("birth_date"):
        flat.setdefault("birth_date", str(personal.get("birth_date"))[:10])
    first = str(cand.first_name or "").strip()
    last = str(cand.last_name or "").strip()
    if first:
        flat.setdefault("first_name", first)
    if last:
        flat.setdefault("last_name", last)
    if first or last:
        flat.setdefault("full_name", f"{first} {last}".strip())
    return extra, personal, flat


async def load_handoff_profile_namespace(
    db: AsyncSession,
    tenant_id: str,
    handoff_id: Optional[str],
    *,
    candidate_id: Optional[str] = None,
) -> dict[str, Any]:
    hid = str(handoff_id or "").strip()
    payload: dict[str, Any] | None = None
    if hid:
        row = (
            await db.execute(
                select(CandidateHandoffSnapshot).where(
                    CandidateHandoffSnapshot.handoff_id == hid,
                    CandidateHandoffSnapshot.agency_tenant_id == str(tenant_id).strip(),
                )
            )
        ).scalar_one_or_none()
        payload = row.payload if row and isinstance(row.payload, dict) else None
    ns = build_handoff_profile_namespace(payload)

    extra, personal, flat = await _load_live_candidate_fields(db, candidate_id)
    ns = merge_flat_into_handoff_candidate(ns, flat)
    return merge_recruiter_transport_fields(
        ns,
        snapshot_payload=payload,
        candidate_extra=extra,
        candidate_personal=personal,
    )


async def load_recruiter_profile_namespace(
    db: AsyncSession,
    tenant_id: str,
    *,
    handoff_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
) -> dict[str, Any]:
    """Handoff snapshot + live candidate fields — primary recruiter SoT for HR verification."""
    if str(handoff_id or "").strip():
        return await load_handoff_profile_namespace(
            db, tenant_id, handoff_id, candidate_id=candidate_id
        )
    extra, personal, flat = await _load_live_candidate_fields(db, candidate_id)
    ns: dict[str, Any] = {"candidate": {}}
    ns = merge_flat_into_handoff_candidate(ns, flat)
    return merge_recruiter_transport_fields(
        ns,
        snapshot_payload=None,
        candidate_extra=extra,
        candidate_personal=personal,
    )
