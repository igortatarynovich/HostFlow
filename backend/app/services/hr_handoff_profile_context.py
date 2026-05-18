"""Map immutable handoff snapshot into HR verification profile context (PR11)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot


def build_handoff_profile_namespace(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten handoff snapshot v1 into paths used by ``_dig(..., 'handoff.candidate.*')``."""
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


async def load_handoff_profile_namespace(
    db: AsyncSession,
    tenant_id: str,
    handoff_id: Optional[str],
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
    if not row or not isinstance(row.payload, dict):
        return {}
    return build_handoff_profile_namespace(row.payload)
