"""Single source of truth: when recruitment (agency tenant) must not mutate candidate/application/docs.

Canon: ``RecruitmentApplication`` in ``handed_off`` locks recruiter writes; or an operational
``CandidateHandoff`` for this agency+candidate with destination in internal_hr / client_portal /
client_account and (status in pending_review / accepted / completed, or ``locked_at`` set while
status is not returned/rejected). Privileged override stays at API layer (administrator /
supervisor / superadmin + ``override_reason``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.hiring_workspace_roles import HIRING_CANDIDATE_MUTATE_ROLES
from backend.app.auth.trust_roles import is_hr_workspace_actor
from backend.app.constants.stages import TERMINAL_STATUSES
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.recruitment_application import RecruitmentApplication

_LOCK_HANDOFF_DESTINATIONS = ("internal_hr", "client_portal", "client_account")
_LOCK_HANDOFF_STATUSES = ("pending_review", "accepted", "completed")

# API bypass: administrator / superadmin / team_lead (legacy supervisor via helper).
RECRUITMENT_LOCK_OVERRIDE_ROLES = frozenset({"administrator", "supervisor", "superadmin"})


def can_override_recruitment_handoff_lock(
    role: str | None,
    preset_id: str | None = None,
    *,
    preferences: dict | None = None,
) -> bool:
    from backend.app.auth.trust_roles import (
        TrustRole,
        is_team_lead_org_actor,
        normalize_trust_role,
    )

    raw = str(role or "").strip().lower()
    if raw in RECRUITMENT_LOCK_OVERRIDE_ROLES:
        return True
    trust = normalize_trust_role(raw)
    if trust in {TrustRole.superadmin.value, TrustRole.administrator.value}:
        return True
    return is_team_lead_org_actor(raw, preset_id, preferences=preferences)

RECRUITMENT_TERMINAL_CLOSE_OVERRIDE = "recruitment_terminal_close"

_RECRUITMENT_MUTATE_ROLE_VALUES = frozenset(
    str(getattr(role, "value", role) or "").strip().lower() for role in HIRING_CANDIDATE_MUTATE_ROLES
) | {"superadmin"}


def is_recruitment_terminal_close_stage(stage_code: str | None) -> bool:
    code = str(stage_code or "").strip().lower()
    return bool(code) and code in TERMINAL_STATUSES


def is_recruitment_terminal_close_payload(payload: dict) -> bool:
    """True when PATCH only closes recruitment (rejected / declined) — allowed under handoff lock."""
    if not payload:
        return False
    stage_raw = payload.get("stage")
    if stage_raw is None:
        stage_raw = payload.get("status")
    if not is_recruitment_terminal_close_stage(str(stage_raw or "")):
        return False
    allowed_keys = {"stage", "status", "status_reason"}
    return set(payload.keys()).issubset(allowed_keys)


async def agency_candidate_has_internal_hr_handoff_lane(
    db: AsyncSession,
    *,
    agency_tenant_id: str,
    candidate_id: str,
) -> bool:
    """True when this agency has an active internal-HR handoff for the candidate (HR operational lane)."""
    tid = str(agency_tenant_id).strip()
    cid = str(candidate_id).strip()
    if not tid or not cid:
        return False
    stmt = (
        select(CandidateHandoff.id)
        .where(
            CandidateHandoff.candidate_id == cid,
            CandidateHandoff.agency_tenant_id == tid,
            CandidateHandoff.destination == "internal_hr",
            or_(
                CandidateHandoff.status.in_(("pending_review", "accepted", "completed")),
                and_(
                    CandidateHandoff.locked_at.isnot(None),
                    CandidateHandoff.status.notin_(("returned", "rejected")),
                ),
            ),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


@dataclass(frozen=True)
class AgencyRecruitmentWriteBypass:
    """Privileged agency write while ``is_recruitment_recruiter_write_locked_by_handoff`` is true."""

    actor_role: str
    override_reason: str


async def require_agency_recruitment_write_allowed(
    db: AsyncSession,
    *,
    agency_tenant_id: str,
    candidate_id: str,
    bypass: Optional[AgencyRecruitmentWriteBypass],
) -> None:
    """Raise ``HTTPException(403)`` when recruitment is locked and no valid privileged bypass.

    Call from candidate/document **service** layers so background/import paths cannot skip the lock
    by bypassing HTTP routers. Client-tenant flows should not call this (they use ``can_client_edit``).
    """
    locked, lock_reason = await is_recruitment_recruiter_write_locked_by_handoff(
        db, agency_tenant_id=agency_tenant_id, candidate_id=candidate_id
    )
    if not locked:
        return
    detail = f"Recruitment locked ({lock_reason or 'handoff'}): cannot modify candidate"
    if bypass is None:
        raise HTTPException(status_code=403, detail=detail)
    role_l = str(bypass.actor_role or "").strip().lower()
    reason = str(bypass.override_reason or "").strip()
    if can_override_recruitment_handoff_lock(role_l) and reason:
        return
    if reason == RECRUITMENT_TERMINAL_CLOSE_OVERRIDE and role_l in _RECRUITMENT_MUTATE_ROLE_VALUES:
        return
    if is_hr_workspace_actor(role_l) and reason == "internal_hr_handoff_lane":
        if await agency_candidate_has_internal_hr_handoff_lane(
            db, agency_tenant_id=agency_tenant_id, candidate_id=candidate_id
        ):
            return
    raise HTTPException(status_code=403, detail=detail)


async def agency_recruitment_lock_bulk_error(
    db: AsyncSession,
    *,
    agency_tenant_id: str,
    candidate_id: str,
    operation_label: str,
) -> Optional[str]:
    """If agency recruitment is locked, return a stable error string for bulk row results; else None."""
    locked, lock_reason = await is_recruitment_recruiter_write_locked_by_handoff(
        db, agency_tenant_id=agency_tenant_id, candidate_id=candidate_id
    )
    if not locked:
        return None
    return f"Recruitment locked ({lock_reason or 'handoff'}): {operation_label}"


async def is_recruitment_recruiter_write_locked_by_handoff(
    db: AsyncSession,
    *,
    agency_tenant_id: str,
    candidate_id: str,
) -> Tuple[bool, Optional[str]]:
    """Return (locked, reason_code) for recruiter-side mutations on this candidate dossier."""
    tid = str(agency_tenant_id).strip()
    cid = str(candidate_id).strip()
    if not tid or not cid:
        return True, "invalid_scope"

    # Intent layer: successful handoff path closed recruitment for this row.
    app_stmt = (
        select(RecruitmentApplication.id)
        .where(
            RecruitmentApplication.tenant_id == tid,
            RecruitmentApplication.candidate_id == cid,
            RecruitmentApplication.status == "handed_off",
        )
        .limit(1)
    )
    if (await db.execute(app_stmt)).scalar_one_or_none() is not None:
        return True, "application_handed_off"

    # Operational handoff: lifecycle still active, or locked_at business-fact without return/reject.
    h_stmt = (
        select(CandidateHandoff.id)
        .where(
            CandidateHandoff.candidate_id == cid,
            CandidateHandoff.agency_tenant_id == tid,
            CandidateHandoff.destination.in_(_LOCK_HANDOFF_DESTINATIONS),
            or_(
                CandidateHandoff.status.in_(_LOCK_HANDOFF_STATUSES),
                and_(
                    CandidateHandoff.locked_at.isnot(None),
                    CandidateHandoff.status.notin_(("returned", "rejected")),
                ),
            ),
        )
        .limit(1)
    )
    if (await db.execute(h_stmt)).scalar_one_or_none() is not None:
        return True, "active_handoff"

    return False, None


__all__ = [
    "RECRUITMENT_LOCK_OVERRIDE_ROLES",
    "RECRUITMENT_TERMINAL_CLOSE_OVERRIDE",
    "AgencyRecruitmentWriteBypass",
    "agency_candidate_has_internal_hr_handoff_lane",
    "agency_recruitment_lock_bulk_error",
    "is_recruitment_terminal_close_payload",
    "is_recruitment_terminal_close_stage",
    "is_recruitment_recruiter_write_locked_by_handoff",
    "require_agency_recruitment_write_allowed",
]
