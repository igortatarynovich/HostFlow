"""Map immutable handoff snapshot + recruitment candidate data into HR verification profile context (PR11)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot

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
    return {
        "candidate": {
            "full_name": full,
            "first_name": first or None,
            "last_name": last or None,
            "citizenship": citizenship,
            "email": contacts.get("email"),
            "phone": contacts.get("phone"),
        },
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


async def load_handoff_profile_namespace(
    db: AsyncSession,
    tenant_id: str,
    handoff_id: Optional[str],
    *,
    candidate_id: Optional[str] = None,
) -> dict[str, Any]:
    hid = str(handoff_id or "").strip()
    if not hid:
        return {}
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

    extra: dict[str, Any] | None = None
    personal: dict[str, Any] | None = None
    cid = str(candidate_id or "").strip()
    if cid:
        from backend.app.models.candidate import Candidate

        cand = await db.get(Candidate, cid)
        if cand:
            extra = cand._get_extra()
            personal = cand._get_personal_data()

    return merge_recruiter_transport_fields(
        ns,
        snapshot_payload=payload,
        candidate_extra=extra,
        candidate_personal=personal,
    )
