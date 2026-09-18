"""Create/revoke typed start_allowed exceptions (narrow write authority)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_start_allowed_exception import WorkforceStartAllowedException
from backend.app.reference.employment_start_allowed import (
    EXCEPTION_BHP_SUCCESSIVE,
    PEM1_EXCEPTION_ALLOWLIST,
    prove_bhp_successive_exception,
)


class StartAllowedExceptionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def exception_to_dict(row: WorkforceStartAllowedException) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "employee_id": row.employee_id,
        "handoff_id": row.handoff_id,
        "requirement_code": row.requirement_code,
        "exception_code": row.exception_code,
        "facts_json": dict(row.facts_json or {}),
        "evidence_refs": list(row.evidence_refs_json or []),
        "actor_user_id": row.actor_user_id,
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
        "revoked_by_user_id": row.revoked_by_user_id,
    }


async def list_active_exceptions(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(WorkforceStartAllowedException).where(
                WorkforceStartAllowedException.tenant_id == tenant_id,
                WorkforceStartAllowedException.employee_id == employee_id,
                WorkforceStartAllowedException.revoked_at.is_(None),
            )
        )
    ).scalars().all()
    return [exception_to_dict(r) for r in rows]


async def create_exception(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    exception_code: str,
    facts: Mapping[str, Any],
    actor_user_id: str | None = None,
    handoff_id: str | None = None,
    evidence_refs: Sequence[Any] | None = None,
    requirement_code: str | None = None,
) -> WorkforceStartAllowedException:
    code = _norm(exception_code)
    if code not in PEM1_EXCEPTION_ALLOWLIST:
        raise StartAllowedExceptionError("exception_code_not_allowlisted", f"Unknown exception {code}")
    req = PEM1_EXCEPTION_ALLOWLIST[code]
    if requirement_code and _norm(requirement_code) != req:
        raise StartAllowedExceptionError(
            "requirement_mismatch",
            f"exception {code} only applies to {req}",
        )
    facts_dict = dict(facts or {})
    if code == EXCEPTION_BHP_SUCCESSIVE:
        violations = prove_bhp_successive_exception(facts_dict)
        if violations:
            raise StartAllowedExceptionError(
                "exception_succession_not_proven",
                ",".join(violations),
            )
    # evidence_refs: only store ids already provided — no document create
    row = WorkforceStartAllowedException(
        id=str(uuid4()),
        tenant_id=tenant_id,
        employee_id=employee_id,
        handoff_id=handoff_id,
        requirement_code=req,
        exception_code=code,
        facts_json=facts_dict,
        evidence_refs_json=list(evidence_refs or []) or None,
        actor_user_id=actor_user_id,
    )
    db.add(row)
    await db.flush()
    return row


async def revoke_exception(
    db: AsyncSession,
    *,
    tenant_id: str,
    exception_id: str,
    actor_user_id: str | None = None,
    reason: str | None = None,
) -> WorkforceStartAllowedException:
    row = await db.get(WorkforceStartAllowedException, exception_id)
    if row is None or row.tenant_id != tenant_id:
        raise StartAllowedExceptionError("exception_not_found", "Exception not found")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        row.revoked_by_user_id = actor_user_id
        row.revoke_reason = reason
        await db.flush()
    return row


__all__ = [
    "StartAllowedExceptionError",
    "exception_to_dict",
    "list_active_exceptions",
    "create_exception",
    "revoke_exception",
]
