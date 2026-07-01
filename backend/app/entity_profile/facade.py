"""Unified Entity Profile facade — registry path + legacy CandidateProfile bridge (P2)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.legacy_bridge import build_legacy_profile_view_from_candidate_profile
from backend.app.entity_profile.resolver import resolve_effective_entity_profile
from backend.app.entity_profile.reverse_map import find_entity_profile_code_by_legacy_candidate_code
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.modules.intake_routing import crud as intake_crud


async def _load_candidate_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_profile_id: Optional[str] = None,
    candidate_profile_code: Optional[str] = None,
) -> CandidateProfile | None:
    pid = str(candidate_profile_id or "").strip()
    code = str(candidate_profile_code or "").strip()
    if pid:
        return (
            await db.execute(
                select(CandidateProfile).where(
                    CandidateProfile.id == pid,
                    CandidateProfile.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
    if code:
        return (
            await db.execute(
                select(CandidateProfile).where(
                    CandidateProfile.code == code,
                    CandidateProfile.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
    return None


async def resolve_entity_profile_facade(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_code: Optional[str] = None,
    candidate_profile_id: Optional[str] = None,
    candidate_profile_code: Optional[str] = None,
    include_presentations: bool = False,
) -> dict[str, Any]:
    """Single read facade for Forms/Intake — registry first when code is explicit."""
    code = str(entity_profile_code or "").strip()
    if code:
        payload = await resolve_effective_entity_profile(
            db,
            tenant_id=str(tenant_id),
            profile_code=code,
            include_presentations=include_presentations,
        )
        if payload.get("resolution_source") == "not_found":
            raise EntityProfileNotFoundError(code)
        payload["bridge_source"] = "entity_profile_registry"
        payload["entity_profile_code"] = code
        payload["warnings"] = []
        payload["candidate_profile_id"] = None
        payload["candidate_profile_code"] = (
            str((payload.get("profile") or {}).get("config", {}).get("legacy_candidate_profile_code") or "").strip()
            or None
        )
        return payload

    legacy_code = str(candidate_profile_code or "").strip()
    if not legacy_code and candidate_profile_id:
        loaded = await _load_candidate_profile(
            db,
            tenant_id=str(tenant_id),
            candidate_profile_id=candidate_profile_id,
        )
        if loaded is not None:
            legacy_code = str(loaded.code or "").strip()

    if legacy_code:
        mapped_code = await find_entity_profile_code_by_legacy_candidate_code(
            db,
            tenant_id=str(tenant_id),
            legacy_candidate_profile_code=legacy_code,
        )
        if mapped_code:
            payload = await resolve_effective_entity_profile(
                db,
                tenant_id=str(tenant_id),
                profile_code=mapped_code,
                include_presentations=include_presentations,
            )
            if payload.get("resolution_source") != "not_found":
                payload["bridge_source"] = "entity_profile_registry"
                payload["entity_profile_code"] = mapped_code
                payload["warnings"] = ["legacy_reverse_map_applied"]
                payload["candidate_profile_code"] = legacy_code
                loaded = await _load_candidate_profile(
                    db,
                    tenant_id=str(tenant_id),
                    candidate_profile_code=legacy_code,
                )
                payload["candidate_profile_id"] = loaded.id if loaded else None
                return payload

    legacy_profile = await _load_candidate_profile(
        db,
        tenant_id=str(tenant_id),
        candidate_profile_id=candidate_profile_id,
        candidate_profile_code=candidate_profile_code,
    )
    if legacy_profile is None:
        return {
            "profile_code": None,
            "entity_profile_code": None,
            "resolution_source": "not_specified",
            "bridge_source": None,
            "profile": None,
            "fields": [],
            "presentations": [],
            "warnings": [],
            "candidate_profile_id": None,
            "candidate_profile_code": None,
        }

    payload = await build_legacy_profile_view_from_candidate_profile(
        db,
        tenant_id=str(tenant_id),
        profile=legacy_profile,
    )
    if legacy_code and "legacy_reverse_map_applied" not in (payload.get("warnings") or []):
        payload["warnings"] = list(payload.get("warnings") or []) + ["legacy_reverse_map_missing"]
    return payload


async def resolve_entity_profile_for_intake_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_source_profile_id: Optional[str] = None,
    entity_profile_code: Optional[str] = None,
    candidate_profile_id: Optional[str] = None,
    candidate_profile_code: Optional[str] = None,
    include_presentations: bool = True,
) -> dict[str, Any]:
    """Resolve entity profile for an intake source — explicit code wins, no silent cross-fallback."""
    explicit_code = str(entity_profile_code or "").strip()
    intake_profile: IntakeSourceProfile | None = None

    if not explicit_code and intake_source_profile_id:
        intake_profile = await intake_crud.get_profile_by_id(
            db,
            tenant_id=str(tenant_id),
            profile_id=str(intake_source_profile_id),
        )
        if intake_profile is not None:
            explicit_code = str(getattr(intake_profile, "entity_profile_code", None) or "").strip()

    payload = await resolve_entity_profile_facade(
        db,
        tenant_id=str(tenant_id),
        entity_profile_code=explicit_code or None,
        candidate_profile_id=candidate_profile_id,
        candidate_profile_code=candidate_profile_code,
        include_presentations=include_presentations,
    )
    if intake_profile is not None:
        payload["intake_source_profile_id"] = intake_profile.id
        payload["intake_source_profile_code"] = intake_profile.code
    return payload
