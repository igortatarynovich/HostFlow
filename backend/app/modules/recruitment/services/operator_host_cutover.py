"""ADR-042 Operator Host Cutover wiring.

Fits uses existing Application process (create/find Candidate) and does not
emit Ready / Transfer. Transfer on Candidate reuses existing stage + package
readiness, then assembles ``ready_for_employment.v1``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models import Lead
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.vacancy import Vacancy
from backend.app.modules.recruitment.services.ready_for_employment_package import (
    FITS_DECISION_KEY,
    OPEN_CANDIDATE_NEXT,
    PREP_KEY,
    build_ready_for_employment_package_v1,
    package_fingerprint_v1,
)
from backend.app.reference.ready_for_employment import (
    CONTRACT_ID,
    TRANSFER_OPERATOR_ACTION,
    validate_ready_for_employment_package_v1,
)

READY_LABEL = "Готов к передаче на трудоустройство"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def record_fits_decision_on_lead(
    lead: Lead,
    *,
    actor_id: str,
    candidate_id: str,
) -> None:
    """Fits completed: person entered Candidates. Not Ready. Not Transfer."""
    norm = _record(getattr(lead, "normalized", None))
    decided_at = _now_iso()
    norm[FITS_DECISION_KEY] = {
        "decision": "fits",
        "decided_at": decided_at,
        "actor_id": actor_id,
        "candidate_id": candidate_id,
    }
    # Never leave a Transfer offer on the Application after Fits.
    prep = _record(norm.get(PREP_KEY))
    prep.pop("transfer_action", None)
    if _text(prep.get("next_action")).lower() in {"offer_handoff", "handed_off"}:
        prep["next_action"] = OPEN_CANDIDATE_NEXT
    norm[PREP_KEY] = prep
    lead.normalized = norm
    if hasattr(lead, "_sa_instance_state"):
        flag_modified(lead, "normalized")
    lead.next_action_type = OPEN_CANDIDATE_NEXT


async def assemble_ready_for_employment_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    actor_id: str,
    application_id: str | None = None,
) -> dict[str, Any]:
    """Build RFE from current Candidate + application facts. Rebuild, never trust a stale snapshot."""
    lead = await _lead_for_candidate(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        application_id=application_id,
    )
    app_id = _text(application_id)
    if not app_id and lead is not None:
        app_id = _text(getattr(lead, "id", None))
    if not app_id:
        app_id = str(candidate.id)

    vac_id = _text(getattr(candidate, "vacancy_id", None))
    if not vac_id and lead is not None:
        vac_id = _text(getattr(lead, "vacancy_id", None))
    vacancy: Vacancy | None = None
    if vac_id:
        vacancy = await db.get(Vacancy, vac_id)

    prior = _record((getattr(lead, "normalized", None) or {}).get(FITS_DECISION_KEY)) if lead else {}
    decided_at = _text(prior.get("decided_at")) or _now_iso()
    actor = _text(actor_id) or _text(prior.get("actor_id")) or "unknown"
    evidence: dict[str, Any] = {
        "source": _text(getattr(lead, "source", None) if lead is not None else None) or "recruitment_candidate",
        "document_ids": [],
    }
    if lead is not None:
        evidence["call_result_v1"] = _record(_record(lead.normalized).get("call_result_v1"))

    stored_pkg = _record(_record((getattr(lead, "normalized", None) or {}).get(PREP_KEY)).get("package"))
    return build_ready_for_employment_package_v1(
        tenant_id=tenant_id,
        application_id=app_id,
        candidate=candidate,
        vacancy=vacancy,
        actor_id=actor,
        decided_at=decided_at,
        evidence=evidence,
        recruitment_facts=_record(stored_pkg.get("recruitment_facts")),
        source_id=_text(getattr(lead, "external_id", None) if lead is not None else None) or None,
    )


async def persist_ready_for_employment_on_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    handoff: CandidateHandoff,
    package: dict[str, Any],
    actor_id: str,
    created: bool,
) -> list[str]:
    """Store validated package on handoff + lead so ESO can resolve it. Returns validator errors."""
    errors = validate_ready_for_employment_package_v1(package)
    if errors:
        return errors

    fp = package_fingerprint_v1(package)
    meta = _record(getattr(handoff, "meta", None))
    meta[PREP_KEY] = {
        "package": package,
        "package_valid": True,
        "package_fingerprint": fp,
        "handoff_id": str(handoff.id),
    }
    handoff.meta = meta

    lead = await _lead_for_candidate(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        application_id=_text(getattr(handoff, "application_id", None)) or None,
    )
    if lead is not None:
        norm = _record(getattr(lead, "normalized", None))
        prep = _record(norm.get(PREP_KEY))
        prep.update(
            {
                "next_action": "handed_off",
                "package": package,
                "package_valid": True,
                "package_fingerprint": fp,
                "handoff_id": str(handoff.id),
                "recruitment_completed_at": _now_iso(),
                "ready_label": READY_LABEL,
                "transfer_action": TRANSFER_OPERATOR_ACTION,
            }
        )
        norm[PREP_KEY] = prep
        lead.normalized = norm
        if hasattr(lead, "_sa_instance_state"):
            flag_modified(lead, "normalized")

    if created:
        from backend.app.core.audit_events import AuditEntityType, AuditEventType
        from backend.app.services.audit import log_audit_event

        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.recruitment_completed,
            entity_type=AuditEntityType.handoff,
            entity_id=str(handoff.id),
            actor_id=actor_id,
            payload={
                "application_id": _text(getattr(handoff, "application_id", None)),
                "candidate_id": str(candidate.id),
                "handoff_id": str(handoff.id),
                "contract_id": CONTRACT_ID,
                "package_fingerprint": fp,
                "message": "Recruitment completed",
            },
        )
    return []


async def _lead_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    application_id: str | None,
) -> Lead | None:
    if application_id:
        lead = await db.get(Lead, application_id)
        if lead is not None:
            return lead
    res = await db.execute(
        select(Lead)
        .where(Lead.tenant_id == tenant_id, Lead.candidate_id == candidate_id)
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


__all__ = [
    "record_fits_decision_on_lead",
    "assemble_ready_for_employment_for_candidate",
    "persist_ready_for_employment_on_handoff",
]
