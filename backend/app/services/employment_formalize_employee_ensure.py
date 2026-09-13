"""Employment Formalize → Employee mint cutover (start_allowed slice 2).

Compose existing ``handoff_from_candidate`` + accept-path operational context.
Does **not** invent a second mint authority.

Locks:
- Mint only when ``authoritative_apply=True`` and ``ready_to_create_employee=True``.
- Formalize evaluate / read with ``ready_to_create_employee=True`` must not mint.
- Idempotency uses existing candidate-scoped ``handoff_from_candidate``; this seam
  stamps ``meta.internal_hr_handoff_id`` for the current handoff so start_allowed
  evaluates the Employee linked to this employment case.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.services import workforce_employees as we_svc
from backend.app.services.workforce_hr_operational_context import ensure_hr_operational_context

POLICY_ID: Final[str] = "employment_formalize_employee_ensure.v1"
ENSURE_API: Final[str] = "ensure_employee_after_formalize_apply"
SKIP_EVALUATE_OR_READ: Final[str] = "evaluate_or_read"
SKIP_NOT_READY: Final[str] = "not_ready_to_create_employee"
SKIP_HANDOFF_NOT_FOUND: Final[str] = "handoff_not_found"
SKIP_CANDIDATE_NOT_FOUND: Final[str] = "candidate_not_found"
SKIP_DELAYED_WORKFORCE: Final[str] = "delayed_workforce_creation"
MINT_CUTOVER_REL: Final[str] = "docs/specs/tasks/employment-start-allowed-mint-cutover.md"


@dataclass(frozen=True)
class FormalizeEmployeeEnsureResult:
    """Outcome of Formalize → Employee ensure (mint or read-only resolve)."""

    employee_id: str | None
    employee_created: bool
    wrote: bool
    skipped_reason: str | None
    handoff_id: str
    linked_handoff_id: str | None
    policy_id: str = POLICY_ID

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "handoff_id": self.handoff_id,
            "employee_id": self.employee_id,
            "employee_created": self.employee_created,
            "wrote": self.wrote,
            "skipped_reason": self.skipped_reason,
            "linked_handoff_id": self.linked_handoff_id,
        }


def should_mint_employee_after_formalize(
    *,
    ready_to_create_employee: bool,
    authoritative_apply: bool,
) -> bool:
    """Pure mint gate: apply/complete + allow-create only. Evaluate never mints."""
    return bool(authoritative_apply) and bool(ready_to_create_employee)


def employee_linked_handoff_id(employee: WorkforceEmployee | None) -> str | None:
    if employee is None:
        return None
    raw = (employee.meta or {}).get("internal_hr_handoff_id")
    text = str(raw or "").strip()
    return text or None


def _stamp_handoff_linkage(employee: WorkforceEmployee, handoff_id: str) -> bool:
    """Bind Employee meta to this handoff. Returns True when meta changed."""
    hid = str(handoff_id).strip()
    md = dict(employee.meta or {})
    if str(md.get("internal_hr_handoff_id") or "").strip() == hid:
        return False
    md["internal_hr_handoff_id"] = hid
    employee.meta = md
    return True


async def ensure_employee_after_formalize_apply(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    actor_user_id: str,
    ready_to_create_employee: bool,
    authoritative_apply: bool,
    hire_date=None,
    seed_hr_bundle: bool = True,
    respect_delayed_workforce_flag: bool = True,
) -> FormalizeEmployeeEnsureResult:
    """Ensure Employee after Formalize allow-create — only on authoritative apply.

    Evaluate / read path (``authoritative_apply=False``):
      - never calls ``handoff_from_candidate``
      - may return an already-linked ``employee_id`` for display (read-only)

    Apply / complete path (``authoritative_apply=True`` + ready):
      - ``handoff_from_candidate`` (idempotent by candidate)
      - stamp ``meta.internal_hr_handoff_id`` to this handoff
      - ``ensure_hr_operational_context`` (accept-path parity)
    """
    tid = str(tenant_id).strip()
    hid = str(handoff_id).strip()
    actor = str(actor_user_id or "").strip() or "system"

    handoff = await db.get(CandidateHandoff, hid)
    if handoff is None:
        return FormalizeEmployeeEnsureResult(
            employee_id=None,
            employee_created=False,
            wrote=False,
            skipped_reason=SKIP_HANDOFF_NOT_FOUND,
            handoff_id=hid,
            linked_handoff_id=None,
        )

    candidate = await db.get(Candidate, str(handoff.candidate_id))
    if candidate is None:
        return FormalizeEmployeeEnsureResult(
            employee_id=None,
            employee_created=False,
            wrote=False,
            skipped_reason=SKIP_CANDIDATE_NOT_FOUND,
            handoff_id=hid,
            linked_handoff_id=None,
        )

    existing = await we_svc.find_employee_by_candidate(db, tid, str(candidate.id))
    linked = employee_linked_handoff_id(existing)

    if not should_mint_employee_after_formalize(
        ready_to_create_employee=ready_to_create_employee,
        authoritative_apply=authoritative_apply,
    ):
        if not ready_to_create_employee:
            reason = SKIP_NOT_READY
        else:
            reason = SKIP_EVALUATE_OR_READ
        # Read-only: only surface employee when already linked to *this* handoff.
        surface_id = str(existing.id) if existing is not None and linked == hid else None
        return FormalizeEmployeeEnsureResult(
            employee_id=surface_id,
            employee_created=False,
            wrote=False,
            skipped_reason=reason,
            handoff_id=hid,
            linked_handoff_id=linked if surface_id else None,
        )

    if respect_delayed_workforce_flag:
        from backend.app.services.tenant_hr_flags import delayed_hr_workforce_creation_enabled

        if await delayed_hr_workforce_creation_enabled(db, tid):
            return FormalizeEmployeeEnsureResult(
                employee_id=None,
                employee_created=False,
                wrote=False,
                skipped_reason=SKIP_DELAYED_WORKFORCE,
                handoff_id=hid,
                linked_handoff_id=linked,
            )

    before_id = str(existing.id) if existing is not None else None
    emp = await we_svc.handoff_from_candidate(
        db,
        tid,
        candidate,
        hire_date=hire_date,
        actor_user_id=actor,
        seed_hr_bundle=seed_hr_bundle,
    )
    created = before_id is None or before_id != str(emp.id)
    # Same candidate → same employee row is the existing handoff_from_candidate guarantee.
    if before_id is not None and before_id == str(emp.id):
        created = False

    linkage_changed = _stamp_handoff_linkage(emp, hid)
    if linkage_changed:
        await db.flush()

    await ensure_hr_operational_context(db, tid, emp)
    await db.flush()

    return FormalizeEmployeeEnsureResult(
        employee_id=str(emp.id),
        employee_created=created,
        wrote=True,
        skipped_reason=None,
        handoff_id=hid,
        linked_handoff_id=hid,
    )


__all__ = [
    "POLICY_ID",
    "ENSURE_API",
    "SKIP_EVALUATE_OR_READ",
    "SKIP_NOT_READY",
    "SKIP_HANDOFF_NOT_FOUND",
    "SKIP_CANDIDATE_NOT_FOUND",
    "SKIP_DELAYED_WORKFORCE",
    "MINT_CUTOVER_REL",
    "FormalizeEmployeeEnsureResult",
    "should_mint_employee_after_formalize",
    "employee_linked_handoff_id",
    "ensure_employee_after_formalize_apply",
]
