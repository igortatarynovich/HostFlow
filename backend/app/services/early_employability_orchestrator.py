"""ESO-2: Early employability evaluate path (Employment-owned).

Read accepted handoff + package + employment context; return
employable / blocked / insufficient_facts. Never creates Employee.
Never called by Recruitment Transfer as completion.
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.reference.early_employability import (
    POLICY_ID,
    evaluate_early_employability_v1,
)
from backend.app.services.employment_accept_orchestrator import (
    resolve_ready_for_employment_package,
)


class EarlyEmployabilityError(Exception):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _text(value: Any) -> str:
    return str(value or "").strip()


async def evaluate_early_employability_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    package: Mapping[str, Any] | None = None,
    employment_context: Mapping[str, Any] | None = None,
    canonical_facts: Mapping[str, Any] | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Employment-owned evaluate. Does not persist Employee. Does not accept."""
    handoff = await db.get(CandidateHandoff, handoff_id)
    if handoff is None:
        raise EarlyEmployabilityError("handoff_not_found", "Handoff not found")

    agency = str(getattr(handoff, "agency_tenant_id", "") or "")
    client = str(getattr(handoff, "client_tenant_id", "") or "")
    if str(tenant_id) not in {agency, client} and agency != str(tenant_id):
        raise EarlyEmployabilityError("handoff_tenant_mismatch", "Handoff does not belong to tenant")

    resolved = await resolve_ready_for_employment_package(db, handoff=handoff, package=package)

    # Merge thin context defaults from package target_work when omitted.
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

    decision = evaluate_early_employability_v1(
        package=resolved,
        handoff_status=_text(getattr(handoff, "status", None)),
        employment_context=ctx,
        canonical_facts=canonical_facts,
        employment_missing=employment_missing,
    )

    return {
        **decision,
        "policy_id": POLICY_ID,
        "handoff_id": str(handoff.id),
        "employee_id": None,
        "employee_created": False,
    }


__all__ = [
    "EarlyEmployabilityError",
    "evaluate_early_employability_for_handoff",
]
