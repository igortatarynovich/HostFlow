"""ESO-4: Employment formalize (Employment-owned).

Derive required formal actions → resolve only missing → emit
ready_to_create_employee when complete. Does not create Employee / HR card.
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.reference.employment_formalize import (
    POLICY_ID,
    apply_employment_formalize_v1,
)
from backend.app.services.employment_accept_orchestrator import (
    resolve_ready_for_employment_package,
)


class EmploymentFormalizeError(Exception):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _text(value: Any) -> str:
    return str(value or "").strip()


async def formalize_employment_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    package: Mapping[str, Any] | None = None,
    employment_context: Mapping[str, Any] | None = None,
    formalize_patch: Mapping[str, Any] | None = None,
    confirmed_actions: Mapping[str, Any] | list[Any] | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
    require_patch_when_missing: bool = False,
) -> dict[str, Any]:
    """Employment-owned formalize. Does not mint Employee. Does not Started."""
    handoff = await db.get(CandidateHandoff, handoff_id)
    if handoff is None:
        raise EmploymentFormalizeError("handoff_not_found", "Handoff not found")

    agency = str(getattr(handoff, "agency_tenant_id", "") or "")
    client = str(getattr(handoff, "client_tenant_id", "") or "")
    if str(tenant_id) not in {agency, client} and agency != str(tenant_id):
        raise EmploymentFormalizeError("handoff_tenant_mismatch", "Handoff does not belong to tenant")

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

    result = apply_employment_formalize_v1(
        package=resolved,
        handoff_status=_text(getattr(handoff, "status", None)),
        employment_context=ctx,
        formalize_patch=formalize_patch,
        confirmed_actions=confirmed_actions,
        employment_missing=employment_missing,
        require_patch_when_missing=require_patch_when_missing,
    )

    return {
        **result,
        "policy_id": POLICY_ID,
        "handoff_id": str(handoff.id),
        "employee_id": None,
        "employee_created": False,
        "hr_employee_card": False,
    }


__all__ = [
    "EmploymentFormalizeError",
    "formalize_employment_for_handoff",
]
