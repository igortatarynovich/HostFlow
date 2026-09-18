"""ESO-4: Employment formalize (Employment-owned).

Derive required formal actions → resolve only missing → emit
ready_to_create_employee when complete.

Mint cutover (ESA2): on authoritative apply/complete with
ready_to_create_employee=true, compose ensure_employee_after_formalize_apply
(handoff_from_candidate only). Evaluate/read must not mint.
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.boundary.public.models import CandidateHandoff
from backend.app.reference.employment_formalize import (
    POLICY_ID,
    apply_employment_formalize_v1,
)
from backend.app.services.employment_accept_orchestrator import (
    resolve_ready_for_employment_package,
)
from backend.app.services.employment_formalize_employee_ensure import (
    ensure_employee_after_formalize_apply,
)


class EmploymentFormalizeError(Exception):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def formalize_request_is_authoritative_apply(
    *,
    formalize_patch: Mapping[str, Any] | None = None,
    confirmed_actions: Mapping[str, Any] | list[Any] | None = None,
) -> bool:
    """True only for Formalize write/complete intent — never for empty evaluate/read."""
    if isinstance(confirmed_actions, Mapping) and any(
        bool(v) for v in confirmed_actions.values()
    ):
        return True
    if isinstance(confirmed_actions, list) and any(_text(x) for x in confirmed_actions):
        return True
    patch = dict(formalize_patch or {})
    if not patch:
        return False
    # Non-empty patch object is apply/complete intent.
    return True


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
    authoritative_apply: bool | None = None,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    """Employment-owned formalize. Mint only on authoritative apply + ready."""
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

    is_apply = (
        bool(authoritative_apply)
        if authoritative_apply is not None
        else formalize_request_is_authoritative_apply(
            formalize_patch=formalize_patch,
            confirmed_actions=confirmed_actions,
        )
    )

    ensure = await ensure_employee_after_formalize_apply(
        db,
        tenant_id=str(tenant_id),
        handoff_id=str(handoff.id),
        actor_user_id=_text(actor_user_id) or "system",
        ready_to_create_employee=bool(result.get("ready_to_create_employee")),
        authoritative_apply=is_apply,
    )

    return {
        **result,
        "policy_id": POLICY_ID,
        "handoff_id": str(handoff.id),
        "employee_id": ensure.employee_id,
        "employee_created": ensure.employee_created,
        "hr_employee_card": False,
        "employee_ensure_wrote": ensure.wrote,
        "employee_ensure_skipped": ensure.skipped_reason,
        "employee_linked_handoff_id": ensure.linked_handoff_id,
        "authoritative_apply": is_apply,
    }


__all__ = [
    "EmploymentFormalizeError",
    "formalize_request_is_authoritative_apply",
    "formalize_employment_for_handoff",
]
