from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_delete_request import CandidateDeleteRequest
from backend.app.models.user import Role, User
from backend.app.services.audit import log_activity


class CandidateDeleteError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _load_candidate(db: AsyncSession, tenant_id: str, candidate_id: str) -> Candidate:
    stmt = sa.select(Candidate).where(
        Candidate.id == candidate_id, Candidate.tenant_id == tenant_id
    )
    candidate = (await db.execute(stmt)).scalar_one_or_none()
    if not candidate:
        raise CandidateDeleteError("Candidate not found", 404)
    return candidate


async def _load_user(db: AsyncSession, user_id: str) -> Optional[User]:
    stmt = sa.select(User).where(User.id == user_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_delete_request(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    requested_by: str,
    reason: str | None,
) -> Dict[str, Any]:
    candidate = await _load_candidate(db, tenant_id, candidate_id)
    requester = await _load_user(db, requested_by)
    if requester is None or requester.tenant_id != tenant_id:
        raise CandidateDeleteError("Requester not found", 404)
    if requester.role != Role.recruiter:
        raise CandidateDeleteError("Only recruiters can request deletion", 403)
    if not requester.supervisor_id:
        raise CandidateDeleteError("Recruiter must have supervisor", 409)

    existing_stmt = sa.select(CandidateDeleteRequest).where(
        CandidateDeleteRequest.tenant_id == tenant_id,
        CandidateDeleteRequest.candidate_id == candidate_id,
        CandidateDeleteRequest.status == "pending",
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise CandidateDeleteError("Delete request already pending", 409)

    request = CandidateDeleteRequest(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        requested_by=requested_by,
        supervisor_id=requester.supervisor_id,
        reason=reason,
        status="pending",
    )
    db.add(request)
    await db.flush()

    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=requested_by,
        action="candidate.delete_requested",
        target_type="candidate",
        target_id=candidate_id,
        payload={"request_id": request.id},
    )

    return await serialize_request(db, tenant_id=tenant_id, request=request)


async def _serialize_requests(
    db: AsyncSession,
    *,
    tenant_id: str,
    requests: Sequence[CandidateDeleteRequest],
) -> List[Dict[str, Any]]:
    if not requests:
        return []

    candidate_ids = {req.candidate_id for req in requests}
    user_ids = {
        req.requested_by for req in requests if req.requested_by
    } | {req.supervisor_id for req in requests if req.supervisor_id}

    candidate_map: Dict[str, Candidate] = {}
    if candidate_ids:
        candidate_rows = await db.execute(
            sa.select(Candidate)
            .where(Candidate.id.in_(candidate_ids))
            .where(Candidate.tenant_id == tenant_id)
        )
        candidate_map = {cand.id: cand for cand in candidate_rows.scalars()}

    user_map: Dict[str, User] = {}
    if user_ids:
        user_rows = await db.execute(sa.select(User).where(User.id.in_(user_ids)))
        user_map = {usr.id: usr for usr in user_rows.scalars()}

    def _user_summary(user: Optional[User]) -> Dict[str, Any] | None:
        if user is None:
            return None
        role_value = user.role.value if isinstance(user.role, Role) else str(user.role)
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "short_id": user.short_id,
            "role": role_value,
        }

    payloads: List[Dict[str, Any]] = []
    for req in requests:
        candidate = candidate_map.get(req.candidate_id)
        payload: Dict[str, Any] = {
            "id": req.id,
            "tenant_id": req.tenant_id,
            "candidate_id": req.candidate_id,
            "requested_by": req.requested_by,
            "supervisor_id": req.supervisor_id,
            "reason": req.reason,
            "status": req.status,
            "created_at": req.created_at,
            "resolved_at": req.resolved_at,
            "resolved_by": req.resolved_by,
            "candidate": {
                "id": candidate.id if candidate else req.candidate_id,
                "first_name": candidate.first_name if candidate else None,
                "last_name": candidate.last_name if candidate else None,
                "email": candidate.email if candidate else None,
                "manager": candidate.manager if candidate else None,
            }
            if candidate
            else None,
            "requested_by_user": _user_summary(user_map.get(req.requested_by)),
            "supervisor_user": _user_summary(user_map.get(req.supervisor_id)),
        }
        payloads.append(payload)
    return payloads


async def serialize_request(
    db: AsyncSession,
    *,
    tenant_id: str,
    request: CandidateDeleteRequest,
) -> Dict[str, Any]:
    serialized = await _serialize_requests(db, tenant_id=tenant_id, requests=[request])
    return serialized[0]


async def list_requests(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: str | None,
    supervisor_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    stmt = sa.select(CandidateDeleteRequest).where(
        CandidateDeleteRequest.tenant_id == tenant_id
    )
    if status:
        stmt = stmt.where(CandidateDeleteRequest.status == status)
    if supervisor_id:
        stmt = stmt.where(CandidateDeleteRequest.supervisor_id == supervisor_id)
    stmt = stmt.order_by(CandidateDeleteRequest.created_at.desc()).limit(limit)
    rows = await db.execute(stmt)
    requests = list(rows.scalars())
    return await _serialize_requests(db, tenant_id=tenant_id, requests=requests)


async def resolve_request(
    db: AsyncSession,
    *,
    tenant_id: str,
    request_id: str,
    actor_id: str,
    approve: bool,
    comment: str | None = None,
) -> Dict[str, Any]:
    stmt = sa.select(CandidateDeleteRequest).where(
        CandidateDeleteRequest.id == request_id,
        CandidateDeleteRequest.tenant_id == tenant_id,
    )
    request = (await db.execute(stmt)).scalar_one_or_none()
    if not request:
        raise CandidateDeleteError("Request not found", 404)
    if request.status != "pending":
        raise CandidateDeleteError("Request already resolved", 409)

    candidate = await _load_candidate(db, tenant_id, request.candidate_id)
    actor = await _load_user(db, actor_id)
    if actor is None or actor.tenant_id != tenant_id:
        raise CandidateDeleteError("Actor not found", 404)
    if actor.role not in (Role.administrator, Role.supervisor):
        raise CandidateDeleteError("Forbidden", 403)
    if actor.role == Role.supervisor and actor.id != request.supervisor_id:
        raise CandidateDeleteError("Supervisor can only resolve own requests", 403)

    request.status = "approved" if approve else "rejected"
    request.resolved_at = _now()
    request.resolved_by = actor_id

    if approve:
        candidate.deleted_at = _now()
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="candidate.delete_approved",
            target_type="candidate",
            target_id=candidate.id,
            payload={"request_id": request.id, "comment": comment},
        )
    else:
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="candidate.delete_rejected",
            target_type="candidate",
            target_id=candidate.id,
            payload={"request_id": request.id, "comment": comment},
        )

    await db.flush()
    return await serialize_request(db, tenant_id=tenant_id, request=request)
