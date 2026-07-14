"""Requirement policy assignment and pin service (ADR-018 PR 2A)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE, DRIVER_CE_UA_PROFILE_CODE
from backend.app.models.candidate import Candidate
from backend.app.requirement_rules.requirement_policy_registry import (
    default_policy_ref_for_entity_profile,
    get_requirement_policy,
)
from backend.app.requirement_rules.readiness_bridge import resolve_entity_profile_code_for_candidate


async def resolve_policy_ref_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Optional[str]:
    """Return pinned policy ref or resolve default from entity profile without pinning."""
    pinned = str(getattr(candidate, "requirement_policy_ref", "") or "").strip()
    if pinned:
        return pinned

    entity_profile = await resolve_entity_profile_code_for_candidate(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
    )
    if entity_profile:
        return default_policy_ref_for_entity_profile(entity_profile)

    vacancy_id = str(getattr(candidate, "vacancy_id", "") or "").strip()
    if vacancy_id:
        return default_policy_ref_for_entity_profile(DRIVER_CE_PROFILE_CODE)
    return None


async def pin_requirement_policy(
    db: AsyncSession,
    *,
    candidate: Candidate,
    policy_ref: str,
    force: bool = False,
) -> str:
    """Pin immutable policy version on candidate. Returns effective policy_ref."""
    ref = str(policy_ref or "").strip()
    if not ref:
        raise ValueError("policy_ref required")
    if get_requirement_policy(ref) is None:
        raise ValueError(f"unknown policy_ref: {ref}")

    existing = str(getattr(candidate, "requirement_policy_ref", "") or "").strip()
    if existing and not force:
        if existing != ref:
            raise ValueError(
                f"candidate already pinned to {existing}; use force=True to override"
            )
        return existing

    candidate.requirement_policy_ref = ref
    if not getattr(candidate, "requirement_policy_pinned_at", None):
        candidate.requirement_policy_pinned_at = datetime.now(timezone.utc)
    await db.flush()
    return ref


async def ensure_driver_ce_policy_pin(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Optional[str]:
    """Pin default Driver CE policy when entity profile matches and no pin exists."""
    if str(getattr(candidate, "requirement_policy_ref", "") or "").strip():
        return candidate.requirement_policy_ref

    entity_profile = await resolve_entity_profile_code_for_candidate(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
    )
    if entity_profile not in {DRIVER_CE_PROFILE_CODE, DRIVER_CE_UA_PROFILE_CODE}:
        return None

    policy_ref = default_policy_ref_for_entity_profile(entity_profile)
    if not policy_ref:
        return None
    return await pin_requirement_policy(db, candidate=candidate, policy_ref=policy_ref)


__all__ = [
    "ensure_driver_ce_policy_pin",
    "pin_requirement_policy",
    "resolve_policy_ref_for_candidate",
]
