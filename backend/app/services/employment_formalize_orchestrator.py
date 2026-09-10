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
    read_employment_spine,
    resolve_ready_for_employment_package,
    write_employment_spine,
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
            if not _text(ctx.get("employment_country")) and (
                target.get("employment_country") or target.get("country")
            ):
                ctx.setdefault(
                    "employment_country",
                    target.get("employment_country") or target.get("country"),
                )
    if not _text(ctx.get("employment_country")):
        ctx.setdefault("employment_country", "PL")

    stored = read_employment_spine(handoff)
    stored_confirmed = stored.get("confirmed_actions")
    merged_confirmed = confirmed_actions if confirmed_actions is not None else stored_confirmed

    result = apply_employment_formalize_v1(
        package=resolved,
        handoff_status=_text(getattr(handoff, "status", None)),
        employment_context=ctx,
        formalize_patch=formalize_patch,
        confirmed_actions=merged_confirmed,
        employment_missing=employment_missing,
        require_patch_when_missing=require_patch_when_missing,
    )

    next_action = "formalize"
    if result.get("ready_to_create_employee"):
        next_action = "confirm_physical_start"
    elif result.get("ready_to_formalize"):
        next_action = "formalize"
    write_employment_spine(
        handoff,
        {
            "confirmed_actions": list(result.get("confirmed_actions") or []),
            "ready_to_formalize": bool(result.get("ready_to_formalize")),
            "ready_to_create_employee": bool(result.get("ready_to_create_employee")),
            "next_action": next_action,
            "decision": result.get("decision"),
        },
    )

    return {
        **result,
        "policy_id": POLICY_ID,
        "handoff_id": str(handoff.id),
        "employee_id": None,
        "employee_created": False,
        "hr_employee_card": False,
        "next_action": next_action,
    }


__all__ = [
    "EmploymentFormalizeError",
    "formalize_employment_for_handoff",
]
