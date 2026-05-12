from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.app.constants.stages import TERMINAL_STATUSES
from backend.app.models import (
    Candidate,
    CandidateAssigneeHistory,
    Vacancy,
    VacancyRecruiter,
)
from backend.app.models.access import UserCompanyAccess
from backend.app.models.user import Role as UserRole, User
from backend.app.services.handoff import is_client_tenant
from backend.app.services.recruitment_handoff_write_guard import (
    AgencyRecruitmentWriteBypass,
    require_agency_recruitment_write_allowed,
)


# Phase 2.6.G-5 Stage C — machine-readable codes for
# ``candidate_assignee_history.reason``. Kept as constants (not an Enum) to
# stay forward-compatible: new reason values can be introduced without a
# schema migration, but every call-site inside this repo SHOULD pick one of
# the documented values below so the audit trail stays queryable. The column
# is ``String(32)`` — keep values short (<= 24 chars leaves slack for
# renames).
CANDIDATE_REASSIGNMENT_REASONS: frozenset[str] = frozenset(
    {
        # Candidate just created; initial recruiter_id at INSERT time.
        "candidate_create",
        # Manual single-candidate PATCH from /app/candidates/:id or router.
        "manual_single",
        # Bulk-set-manager endpoint (currently writes ``Candidate.manager``;
        # Stage D will route it through the shadow-write helper).
        "manual_bulk",
        # Fresh candidate born from a meta-lead conversion, recruiter picked
        # via vacancy pool / vacancy.manager (``resolve_vacancy_primary_recruiter``).
        "lead_vacancy",
        # Fresh candidate born from a meta-lead conversion, recruiter stamped
        # explicitly by the lead-qualification rule (rule-side override).
        "lead_rule",
        # Fresh candidate born from a meta-lead conversion — neither rule nor
        # vacancy produced a recruiter, fell into tenant-wide fallback
        # (``MetaLeadSettings.fallback_recruiter_id`` / hint).
        "lead_fallback",
        # Manual lead re-route to another vacancy (API endpoint) —
        # recruiter picked from the target vacancy's pool / manager.
        "lead_reroute_vacancy",
        # Manual lead re-route + rule stamped explicit recruiter_id.
        "lead_reroute_rule",
        # Manual lead re-route — fallback branch (tenant hint).
        "lead_reroute_fallback",
        # Admin-side override (platform admin reassigning without going
        # through the usual flow).
        "admin",
        # Time-off re-route (future G-4 Stage / Stage D integration).
        "timeoff_reroute",
    }
)


def _normalise_owner_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AssignmentDecision:
    recruiter_id: Optional[str]
    strategy: str
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def assigned(self) -> bool:
        return bool(self.recruiter_id)


async def _load_vacancy(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: Optional[str],
) -> Optional[Vacancy]:
    if not vacancy_id:
        return None
    row = await db.execute(
        select(Vacancy).where(
            Vacancy.id == vacancy_id,
            Vacancy.tenant_id == tenant_id,
        )
    )
    return row.scalar_one_or_none()


async def _load_active_user(
    db: AsyncSession,
    tenant_id: str,
    user_id: Optional[str],
    *,
    allowed_roles: Optional[Sequence[UserRole]] = None,
) -> Optional[User]:
    if not user_id:
        return None
    stmt = select(User).where(
        User.id == user_id,
        User.is_active.is_(True),
        or_(User.tenant_id.is_(None), User.tenant_id == tenant_id),
    )
    if allowed_roles:
        stmt = stmt.where(User.role.in_(list(allowed_roles)))
    row = await db.execute(stmt)
    return row.scalar_one_or_none()


async def _fetch_candidate_loads(
    db: AsyncSession,
    tenant_id: str,
    recruiter_ids: Iterable[str],
) -> Dict[str, int]:
    ids = {rid for rid in recruiter_ids if rid}
    if not ids:
        return {}
    stmt = (
        select(Candidate.recruiter_id, func.count())
        .where(
            Candidate.tenant_id == tenant_id,
            Candidate.recruiter_id.in_(sorted(ids)),
        )
        .group_by(Candidate.recruiter_id)
    )
    if TERMINAL_STATUSES:
        stmt = stmt.where(~Candidate.status.in_(list(TERMINAL_STATUSES)))
    rows = await db.execute(stmt)
    return {str(rid): int(total or 0) for rid, total in rows.all()}


def _choose_by_score(
    pool: Sequence[Dict[str, Any]],
    loads: Dict[str, int],
    *,
    default_weight: int = 1,
) -> Optional[Dict[str, Any]]:
    scored: List[Tuple[float, int, datetime, str, Dict[str, Any]]] = []
    for entry in pool:
        recruiter_id = entry["user_id"]
        weight = entry.get("weight") or default_weight
        load = loads.get(recruiter_id, 0)
        score = weight / max(1, load)
        last_assigned_at: Optional[datetime] = entry.get("last_assigned_at")
        # Treat NULL last_assigned as the earliest possible timestamp
        rotation_marker = last_assigned_at or datetime.fromtimestamp(0, tz=timezone.utc)
        scored.append((score, load, rotation_marker, recruiter_id, entry))

    if not scored:
        return None

    scored.sort(
        key=lambda item: (
            -item[0],             # prefer higher score
            item[1],              # then lower load
            item[2],              # then oldest assignment (round-robin)
            item[3],              # deterministic tie breaker
        )
    )
    return scored[0][-1]


async def _prepare_vacancy_pool(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
) -> List[Dict[str, Any]]:
    recruiter_alias = aliased(User)
    rows = await db.execute(
        select(
            VacancyRecruiter.user_id,
            VacancyRecruiter.weight,
            VacancyRecruiter.last_assigned_at,
            recruiter_alias.full_name,
            recruiter_alias.short_id,
        )
        .join(
            recruiter_alias,
            and_(
                recruiter_alias.id == VacancyRecruiter.user_id,
                recruiter_alias.is_active.is_(True),
                recruiter_alias.role == UserRole.recruiter,
                or_(
                    recruiter_alias.tenant_id.is_(None),
                    recruiter_alias.tenant_id == tenant_id,
                ),
            ),
        )
        .where(
            VacancyRecruiter.vacancy_id == vacancy_id,
            VacancyRecruiter.tenant_id == tenant_id,
            VacancyRecruiter.is_active.is_(True),
        )
    )
    return [
        {
            "user_id": row.user_id,
            "weight": row.weight,
            "last_assigned_at": row.last_assigned_at,
            "full_name": row.full_name,
            "short_id": row.short_id,
        }
        for row in rows.all()
    ]


async def _prepare_company_supervisors(
    db: AsyncSession,
    tenant_id: str,
    company_id: Optional[str],
) -> List[Dict[str, Any]]:
    if not company_id:
        return []
    user_alias = aliased(User)
    rows = await db.execute(
        select(
            user_alias.id,
            user_alias.full_name,
            user_alias.short_id,
            user_alias.role,
        )
        .join(
            UserCompanyAccess,
            and_(
                UserCompanyAccess.user_id == user_alias.id,
                UserCompanyAccess.company_id == company_id,
                UserCompanyAccess.tenant_id == tenant_id,
            ),
        )
        .where(
            user_alias.is_active.is_(True),
            user_alias.role.in_([UserRole.supervisor, UserRole.administrator]),
            or_(
                user_alias.tenant_id.is_(None),
                user_alias.tenant_id == tenant_id,
            ),
        )
    )
    return [
        {
            "user_id": row.id,
            "full_name": row.full_name,
            "short_id": row.short_id,
            "role": row.role.value if hasattr(row.role, "value") else str(row.role),
        }
        for row in rows.all()
    ]


async def _prepare_tenant_admins(db: AsyncSession, tenant_id: str) -> List[Dict[str, Any]]:
    rows = await db.execute(
        select(User.id, User.full_name, User.short_id)
        .where(
            User.tenant_id == tenant_id,
            User.role == UserRole.administrator,
            User.is_active.is_(True),
        )
    )
    return [
        {
            "user_id": row.id,
            "full_name": row.full_name,
            "short_id": row.short_id,
        }
        for row in rows.all()
    ]


async def assign_recruiter(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> AssignmentDecision:
    decision_context: Dict[str, Any] = {}
    vacancy = await _load_vacancy(db, tenant_id, vacancy_id)
    if vacancy:
        decision_context["vacancy_id"] = vacancy.id
        company_id = vacancy.company_id or company_id
    if company_id:
        decision_context["company_id"] = company_id

    if vacancy_id:
        pool = await _prepare_vacancy_pool(db, tenant_id, vacancy_id)
        decision_context["pool_size"] = len(pool)
        if pool:
            loads = await _fetch_candidate_loads(db, tenant_id, (p["user_id"] for p in pool))
            choice = _choose_by_score(pool, loads)
            if choice:
                await db.execute(
                    update(VacancyRecruiter)
                    .where(
                        VacancyRecruiter.vacancy_id == vacancy_id,
                        VacancyRecruiter.user_id == choice["user_id"],
                        VacancyRecruiter.tenant_id == tenant_id,
                    )
                    .values(last_assigned_at=_now_utc())
                )
                decision_context["strategy"] = "least_load"
                decision_context["loads"] = loads
                decision_context["selected"] = choice
                return AssignmentDecision(
                    recruiter_id=choice["user_id"],
                    strategy="least_load",
                    context=decision_context,
                )

    owner = await _load_active_user(db, tenant_id, getattr(vacancy, "manager", None))
    if owner:
        decision_context["strategy"] = "vacancy_owner"
        decision_context["selected"] = {"user_id": owner.id}
        return AssignmentDecision(
            recruiter_id=owner.id,
            strategy="vacancy_owner",
            context=decision_context,
        )

    supervisors = await _prepare_company_supervisors(db, tenant_id, company_id)
    if supervisors:
        loads = await _fetch_candidate_loads(db, tenant_id, (s["user_id"] for s in supervisors))
        choice = _choose_by_score(supervisors, loads)
        if choice:
            decision_context["strategy"] = "company_supervisor"
            decision_context["loads"] = loads
            decision_context["selected"] = choice
            return AssignmentDecision(
                recruiter_id=choice["user_id"],
                strategy="company_supervisor",
                context=decision_context,
            )

    admins = await _prepare_tenant_admins(db, tenant_id)
    if admins:
        loads = await _fetch_candidate_loads(db, tenant_id, (a["user_id"] for a in admins))
        choice = _choose_by_score(admins, loads)
        if choice:
            decision_context["strategy"] = "tenant_admin"
            decision_context["loads"] = loads
            decision_context["selected"] = choice
            return AssignmentDecision(
                recruiter_id=choice["user_id"],
                strategy="tenant_admin",
                context=decision_context,
            )

    decision_context["strategy"] = "unassigned"
    return AssignmentDecision(
        recruiter_id=None,
        strategy="unassigned",
        context=decision_context,
    )


async def resolve_vacancy_primary_recruiter(
    db: AsyncSession,
    tenant_id: str,
    vacancy: Optional[Vacancy],
) -> Optional[str]:
    """Return the primary recruiter *for this vacancy* or ``None``.

    Phase 2.6.G-5 Stage A — single-purpose helper for call-sites that only want
    vacancy-scoped resolution (no company-supervisor / tenant-admin fallback).

    Cascade (first non-empty wins):

    1. ``VacancyRecruiter`` m2m pool — least-load pick among ``is_active=True``
       rows (mirrors the ``least_load`` strategy of :func:`assign_recruiter`).
    2. ``Vacancy.manager`` — single primary owner, validated to be an active
       user within the tenant.
    3. ``None`` — caller decides whether to fall back further (e.g. to
       ``MetaLeadSettings.fallback_recruiter_id``).

    Replaces the silent dead-read ``getattr(vacancy, "recruiter_id", None)``
    that existed in lead processing before Stage A — ``Vacancy`` has no such
    column, so the old path always returned ``None`` and every lead fell
    through to the tenant-wide fallback.

    Contract notes:

    - Never writes to DB; ``last_assigned_at`` update happens only in
      :func:`assign_recruiter`, which remains the entry point for the full
      routing cascade.
    - ``vacancy=None`` → returns ``None`` immediately.
    - Returns a plain ``str`` user-id (not an :class:`AssignmentDecision`) to
      keep it drop-in for places that previously read a bare attribute.
    """
    if vacancy is None:
        return None

    vacancy_id = getattr(vacancy, "id", None)
    if vacancy_id:
        pool = await _prepare_vacancy_pool(db, tenant_id, str(vacancy_id))
        if pool:
            loads = await _fetch_candidate_loads(
                db, tenant_id, (p["user_id"] for p in pool)
            )
            choice = _choose_by_score(pool, loads)
            if choice:
                return str(choice["user_id"])

    manager_id = getattr(vacancy, "manager", None)
    if manager_id:
        owner = await _load_active_user(db, tenant_id, str(manager_id))
        if owner:
            return str(owner.id)

    return None


async def record_candidate_reassignment(
    db: AsyncSession,
    candidate: Candidate,
    *,
    new_recruiter_id: Optional[str],
    reason: str,
    actor: Optional[str] = None,
    actor_kind: str = "user",
    note: Optional[str] = None,
    skip_if_unchanged: bool = True,
    write: bool = True,
    agency_recruitment_bypass: Optional[AgencyRecruitmentWriteBypass] = None,
) -> Optional[CandidateAssigneeHistory]:
    """Reassign a candidate's recruiter and append an audit-trail row.

    Phase 2.6.G-5 Stage C — the **single** write-point for
    :attr:`Candidate.recruiter_id` mutations inside HostFlow. Every code path
    that today does ``candidate.recruiter_id = ...`` ad-hoc is being
    funneled through this helper (see ``docs/specs/manager-assignment.md``
    §4 Stage C for the roll-out list).

    Contract
    --------

    * When ``write=True`` (default) the helper mutates ``candidate.recruiter_id``
      *and* adds a :class:`CandidateAssigneeHistory` row to the session.
      Agency-owned dossiers require ``require_agency_recruitment_write_allowed``
      (pass ``agency_recruitment_bypass`` only from guarded API paths that
      already validated a privileged override).
    * When ``write=False`` the helper **only** emits the history row — useful
      for INSERT-time assignments where ``recruiter_id`` is already baked into
      the ``INSERT`` statement (see ``create_candidate_full``).
    * If ``skip_if_unchanged=True`` (default) and the candidate already has
      ``recruiter_id == new_recruiter_id``, nothing happens and the helper
      returns ``None``. Callers who want to force an audit row on no-op (e.g.
      re-confirming an assignment after a routing loop) should pass
      ``skip_if_unchanged=False``.
    * The helper does **not** commit. It calls ``db.flush()`` so downstream
      logic can read the fresh ``recruiter_id`` in the same transaction.
    * ``reason`` should be one of :data:`CANDIDATE_REASSIGNMENT_REASONS`.
      Values outside the set are accepted (column is ``String(32)``) but
      emit no validation error — stay within the documented vocabulary so
      the audit trail remains queryable.

    Returns
    -------
    The persisted-pending :class:`CandidateAssigneeHistory` row, or ``None``
    when the call was a no-op (``skip_if_unchanged`` + same value) or
    ``candidate`` has no primary key yet (defensive guard).
    """

    if candidate is None:
        return None

    candidate_id = getattr(candidate, "id", None)
    if not candidate_id:
        return None

    tenant_id_attr = getattr(candidate, "tenant_id", None)
    if not tenant_id_attr:
        return None

    if write:
        cand_tid = str(tenant_id_attr).strip()
        if cand_tid and not await is_client_tenant(db, cand_tid):
            await require_agency_recruitment_write_allowed(
                db,
                agency_tenant_id=cand_tid,
                candidate_id=str(candidate_id),
                bypass=agency_recruitment_bypass,
            )

    old_value = _normalise_owner_id(getattr(candidate, "recruiter_id", None))
    new_value = _normalise_owner_id(new_recruiter_id)

    if write and skip_if_unchanged and old_value == new_value:
        # Phase 2.6.G-5 Stage D — even on a no-op ``recruiter_id`` we MUST
        # fix a drifted ``Candidate.manager`` (legacy column; no FK) so the
        # shadow-write invariant holds across the codebase. The
        # ``bulk_set_manager`` endpoint wrote only to ``manager`` before
        # Stage D, so some tenants have ``manager != recruiter_id``; this
        # self-heal path reconciles them without touching the audit trail
        # (history is about reassignments, not mirror-sync).
        legacy_manager = _normalise_owner_id(getattr(candidate, "manager", None))
        if legacy_manager != new_value:
            candidate.manager = new_value
            await db.flush()
        return None

    if write:
        candidate.recruiter_id = new_value
        # Phase 2.6.G-5 Stage D — shadow-write ``Candidate.manager`` to the
        # same value as ``recruiter_id``. Keeps the UI filter ``?manager=X``
        # (used by ``/app/candidates`` until Stage F) parity-visible for
        # reassigned candidates, and prevents the split-brain bug
        # documented in ``docs/specs/manager-assignment.md`` §1.2.1 where
        # NBA/notifications/bell read ``recruiter_id`` while the manager
        # filter reads ``manager``.
        candidate.manager = new_value
        await db.flush()

    reason_value = (reason or "").strip() or "unknown"
    if len(reason_value) > 32:
        reason_value = reason_value[:32]

    actor_kind_value = (actor_kind or "user").strip() or "user"
    if len(actor_kind_value) > 16:
        actor_kind_value = actor_kind_value[:16]

    history_row = CandidateAssigneeHistory(
        id=str(uuid.uuid4()),
        tenant_id=str(tenant_id_attr),
        candidate_id=str(candidate_id),
        from_user_id=old_value,
        to_user_id=new_value,
        reason=reason_value,
        actor_user_id=_normalise_owner_id(actor),
        actor_kind=actor_kind_value,
        note=(note or None),
        changed_at=_now_utc(),
    )
    db.add(history_row)
    await db.flush()
    return history_row
