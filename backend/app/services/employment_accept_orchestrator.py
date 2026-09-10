"""ESO-1: Employment-owned accept apply path.

Evaluates ``employment_accept_policy.v1`` and, on ``auto_accept``, calls
existing ``accept_handoff``. Recruitment Transfer must never call this.

Not ESO-2 employability. Not ritual Accept when policy says auto_accept.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.lead import Lead
from backend.app.reference.employment_accept_policy import (
    DECISION_AUTO_ACCEPT,
    EMPLOYMENT_STARTED_MESSAGE,
    POLICY_ID,
    evaluate_employment_accept_policy_v1,
)
from backend.app.reference.ready_for_employment import (
    CONTRACT_ID as RFE_CONTRACT_ID,
    is_valid_ready_for_employment_package_v1,
)
from backend.app.services.audit import log_audit_event
from backend.app.services import handoff as handoff_service

PREP_KEY = "ready_for_employment_prep_v1"
SPINE_KEY = "employment_spine_v1"


class EmploymentAcceptError(Exception):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def resolve_ready_for_employment_package(
    db: AsyncSession,
    *,
    handoff: CandidateHandoff,
    package: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Prefer explicit package; else RSO prep on application/lead if present."""
    if isinstance(package, Mapping) and package:
        return dict(package)

    app_id = _text(getattr(handoff, "application_id", None))
    cand_id = _text(getattr(handoff, "candidate_id", None))
    lead: Lead | None = None
    if app_id:
        lead = await db.get(Lead, app_id)
    if lead is None and cand_id:
        # Best-effort: lead linked by candidate_id
        from sqlalchemy import select

        res = await db.execute(
            select(Lead)
            .where(
                Lead.tenant_id == str(handoff.agency_tenant_id),
                Lead.candidate_id == cand_id,
            )
            .order_by(Lead.created_at.desc())
            .limit(1)
        )
        lead = res.scalar_one_or_none()
    if lead is None:
        return None
    prep = _record(_record(lead.normalized).get(PREP_KEY))
    stored = prep.get("package")
    if isinstance(stored, Mapping) and is_valid_ready_for_employment_package_v1(stored):
        return dict(stored)
    return dict(stored) if isinstance(stored, Mapping) else None


def read_employment_spine(handoff: CandidateHandoff) -> dict[str, Any]:
    """Employment-owned continuation state on the handoff (not an HR card)."""
    return _record(_record(getattr(handoff, "meta", None)).get(SPINE_KEY))


def write_employment_spine(handoff: CandidateHandoff, patch: Mapping[str, Any]) -> dict[str, Any]:
    """Persist Employment next_action / confirmed formal items on the same handoff."""
    meta = _record(getattr(handoff, "meta", None))
    spine = {**_record(meta.get(SPINE_KEY)), **dict(patch)}
    meta[SPINE_KEY] = spine
    handoff.meta = meta
    flag_modified(handoff, "meta")
    return spine


async def apply_employment_accept_policy(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    actor_id: str | None,
    package: Mapping[str, Any] | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Employment-owned apply. Auto-accepts via ``accept_handoff`` when policy allows."""
    handoff = await db.get(CandidateHandoff, handoff_id)
    if handoff is None:
        raise EmploymentAcceptError("handoff_not_found", "Handoff not found")
    if str(handoff.agency_tenant_id) != str(tenant_id) and str(getattr(handoff, "client_tenant_id", "") or "") != str(
        tenant_id
    ):
        # Accepting tenant must be agency or client tenant on the handoff.
        if str(handoff.agency_tenant_id) != str(tenant_id):
            raise EmploymentAcceptError("handoff_tenant_mismatch", "Handoff does not belong to tenant")

    resolved = await resolve_ready_for_employment_package(db, handoff=handoff, package=package)
    dest = _text(getattr(handoff, "destination", None)) or "internal_hr"

    # Link-level enablement (best-effort).
    handoff_enabled = True
    try:
        from backend.app.services.tenant_links import get_tenant_link

        link = await get_tenant_link(
            db,
            agency_tenant_id=str(handoff.agency_tenant_id),
            client_company_id=getattr(handoff, "client_company_id", None),
            client_tenant_id=getattr(handoff, "client_tenant_id", None),
        )
        if link is not None:
            handoff_enabled = bool(link.get_handoff_enabled())
            if dest == "internal_hr" and hasattr(link, "get_handoff_to_internal_hr"):
                handoff_enabled = handoff_enabled and bool(link.get_handoff_to_internal_hr())
    except Exception:  # noqa: BLE001 — policy still evaluates package
        pass

    decision = evaluate_employment_accept_policy_v1(
        package=resolved,
        handoff_status=_text(getattr(handoff, "status", None)),
        employment_missing=employment_missing,
        destination=dest,
        handoff_enabled=handoff_enabled,
    )

    result: dict[str, Any] = {
        "policy_id": POLICY_ID,
        "handoff_id": str(handoff.id),
        "decision": decision["decision"],
        "ritual_accept_forbidden": decision.get("ritual_accept_forbidden"),
        "blockers": decision.get("blockers") or [],
        "employment_missing": decision.get("employment_missing") or [],
        "reuse_violations": decision.get("reuse_violations") or [],
        "package_valid": decision.get("package_valid"),
        "accepted": False,
        "employment_started": False,
        "employee_id": None,
        "message": None,
    }

    if decision["decision"] != DECISION_AUTO_ACCEPT:
        result["message"] = "Employment accept requires review or package fix"
        return result

    accepted, err = await handoff_service.accept_handoff(
        db,
        handoff_id=str(handoff.id),
        reviewed_by_user_id=_text(actor_id) or None,
        tenant_id=str(tenant_id),
    )
    if err or accepted is None:
        raise EmploymentAcceptError(
            "accept_failed",
            str(err or "accept_handoff failed"),
        )

    await log_audit_event(
        db,
        tenant_id=str(tenant_id),
        event_type=AuditEventType.employment_started,
        entity_type=AuditEntityType.handoff,
        entity_id=str(accepted.id),
        actor_id=_text(actor_id) or None,
        payload={
            "message": EMPLOYMENT_STARTED_MESSAGE,
            "handoff_id": str(accepted.id),
            "candidate_id": str(accepted.candidate_id),
            "policy_id": POLICY_ID,
            "package_contract_id": RFE_CONTRACT_ID,
            "application_id": _text(getattr(accepted, "application_id", None)) or None,
            "started_at": _now_iso(),
        },
    )

    result["accepted"] = True
    result["employment_started"] = True
    result["message"] = EMPLOYMENT_STARTED_MESSAGE
    # Employee may or may not materialize depending on delayed HR flag — ESO-1 does not own that depth.
    return result


__all__ = [
    "EmploymentAcceptError",
    "resolve_ready_for_employment_package",
    "apply_employment_accept_policy",
    "read_employment_spine",
    "write_employment_spine",
    "SPINE_KEY",
]
