"""ESO-3: Employment missing resolution (Employment-owned).

Apply minimal fact/evidence patch → auto re-evaluate early employability →
return active items only. Never creates Employee. Never dumps a full checklist.
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.reference.employment_missing_resolution import (
    POLICY_ID,
    apply_employment_resolution_v1,
)
from backend.app.services.employment_accept_orchestrator import (
    resolve_ready_for_employment_package,
)


class EmploymentMissingResolutionError(Exception):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _text(value: Any) -> str:
    return str(value or "").strip()


async def resolve_employment_missing_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    package: Mapping[str, Any] | None = None,
    employment_context: Mapping[str, Any] | None = None,
    resolution_patch: Mapping[str, Any] | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
    require_patch_when_not_ready: bool = False,
) -> dict[str, Any]:
    """Employment-owned resolve. Does not persist Employee. Does not Formalize."""
    handoff = await db.get(CandidateHandoff, handoff_id)
    if handoff is None:
        raise EmploymentMissingResolutionError("handoff_not_found", "Handoff not found")

    agency = str(getattr(handoff, "agency_tenant_id", "") or "")
    client = str(getattr(handoff, "client_tenant_id", "") or "")
    if str(tenant_id) not in {agency, client} and agency != str(tenant_id):
        raise EmploymentMissingResolutionError(
            "handoff_tenant_mismatch",
            "Handoff does not belong to tenant",
        )

    resolved = await resolve_ready_for_employment_package(db, handoff=handoff, package=package)

    ctx: dict[str, Any] = dict(employment_context or {})
    if isinstance(resolved, Mapping):
        target = resolved.get("target_work")
        if isinstance(target, Mapping):
            if not _text(ctx.get("employer_id")) and target.get("employer_id"):
                ctx.setdefault("employer_id", target.get("employer_id"))
            if not _text(ctx.get("vacancy_id")) and target.get("vacancy_id"):
                ctx.setdefault("vacancy_id", target.get("vacancy_id"))
            if not _text(ctx.get("position_category")) and target.get("position_category"):
                ctx.setdefault("position_category", target.get("position_category"))

    result = apply_employment_resolution_v1(
        package=resolved,
        handoff_status=_text(getattr(handoff, "status", None)),
        employment_context=ctx,
        resolution_patch=resolution_patch,
        employment_missing=employment_missing,
        require_patch_when_not_ready=require_patch_when_not_ready,
    )

    return {
        **result,
        "policy_id": POLICY_ID,
        "handoff_id": str(handoff.id),
        "employee_id": None,
        "employee_created": False,
    }


__all__ = [
    "EmploymentMissingResolutionError",
    "resolve_employment_missing_for_handoff",
]
