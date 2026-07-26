"""ADR-031 §2.4 — early Candidate shell + Application for Recruitment compliance outbound.

Does not send mail. Does not mark Lead as processed / converted for UI
(``lead.candidate_id`` stays unset until Process reuses the shell).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.acquisition.candidate_activity import read_acquisition_routing_stamp
from backend.app.api.v1.candidates.service import create_candidate_full
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.modules.recruitment.services.application_result_service import (
    ApplicationTransportConflictError,
    ensure_application_result_for_transport_lead,
)

SHELL_EXTRA_KEY = "compliance_candidate_shell_v1"
SHELL_SOURCE_KEY = "compliance_shell_source"

_SALES_ROUTE_INTENTS = frozenset(
    {"sales_inquiry", "client_inquiry", "inquiry", "service_request", "partner_inquiry"}
)


class ComplianceOutboundEnsureError(Exception):
    code = "compliance_outbound_ensure_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class ComplianceOutboundEnsureResult:
    candidate_id: str
    application_id: str
    created_shell: bool
    created_application: bool


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _intake_result_link(lead: Lead) -> dict[str, Any]:
    return _record(_record(getattr(lead, "normalized", None)).get("intake_result_link_v1"))


def lead_is_sales_bound_for_recruitment_ensure(lead: Lead) -> bool:
    link = _intake_result_link(lead)
    if link.get("sales_inquiry_id") or str(link.get("result_type") or "") == "sales_inquiry":
        return True
    stamp = read_acquisition_routing_stamp(lead)
    route = str(stamp.get("route_intent") or "").strip().lower()
    return route in _SALES_ROUTE_INTENTS


def lead_has_recruitment_intent(lead: Lead) -> bool:
    """§2.4.1 — vacancy or explicit pool intent."""
    if getattr(lead, "vacancy_id", None):
        return True
    if getattr(lead, "funnel_id", None):
        return True
    norm = _record(getattr(lead, "normalized", None))
    return norm.get("recruitment_pool_intent_v1") is True


def lead_is_recruitment_destination_for_compliance(lead: Lead) -> bool:
    """§2.4.2 — Recruitment destination, not Sales."""
    if lead_is_sales_bound_for_recruitment_ensure(lead):
        return False
    link = _intake_result_link(lead)
    if link.get("application_id") or str(link.get("result_type") or "") == "application":
        return True
    stamp = read_acquisition_routing_stamp(lead)
    route = str(stamp.get("route_intent") or "").strip().lower()
    if route in {"candidate_application", "candidate"}:
        return True
    # Meta vacancy mapping leaves vacancy_id without always stamping route yet.
    return lead_has_recruitment_intent(lead)


def _shell_extra(source: str) -> dict[str, Any]:
    return {
        SHELL_EXTRA_KEY: True,
        SHELL_SOURCE_KEY: str(source or "compliance_outbound")[:64],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _candidate_payload_from_lead(lead: Lead, *, source: str) -> dict[str, Any]:
    norm = _record(getattr(lead, "normalized", None))
    first = str(norm.get("first_name") or "").strip()
    last = str(norm.get("last_name") or "").strip()
    full = str(norm.get("full_name") or "").strip()
    if not first and full:
        parts = full.split(None, 1)
        first = parts[0] if parts else ""
        last = parts[1] if len(parts) > 1 else ""
    email = str(norm.get("email") or "").strip() or None
    phone = str(norm.get("phone") or "").strip() or None
    extra = _shell_extra(source)
    payload: dict[str, Any] = {
        "first_name": first or "Lead",
        "last_name": last or "Shell",
        "email": email,
        "phone": phone,
        "phone_country_code": norm.get("phone_country_code"),
        "own_company_id": getattr(lead, "own_company_id", None),
        "company_id": getattr(lead, "company_id", None),
        "vacancy_id": getattr(lead, "vacancy_id", None),
        "contacts": {
            key: value
            for key, value in {
                "email": email,
                "phone": phone,
                "phone_country_code": norm.get("phone_country_code"),
            }.items()
            if value
        },
        "source": str(getattr(lead, "source", None) or source or "meta")[:64],
        "origin": {"compliance_outbound_shell": True, "lead_id": str(lead.id)},
        "extra": extra,
    }
    return payload


async def _application_for_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> Optional[RecruitmentApplication]:
    return await db.scalar(
        select(RecruitmentApplication)
        .where(
            RecruitmentApplication.tenant_id == tenant_id,
            RecruitmentApplication.lead_id == lead_id,
        )
        .limit(1)
    )


async def find_compliance_shell_candidate_for_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> Optional[Candidate]:
    """Return Candidate linked via Application.lead_id (early shell or later conversion)."""
    tid = str(tenant_id).strip()
    lid = str(getattr(lead, "id", "") or "").strip()
    if not tid or not lid:
        return None
    app = await _application_for_lead(db, tenant_id=tid, lead_id=lid)
    if app is None:
        return None
    cand = await db.get(Candidate, str(app.candidate_id))
    if cand is None or str(cand.tenant_id) != tid or cand.deleted_at is not None:
        return None
    return cand


async def attach_compliance_shell_candidate_on_process(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> Optional[Candidate]:
    """Process reuse: link ``lead.candidate_id`` to early Application's Candidate (idempotent)."""
    if getattr(lead, "candidate_id", None):
        existing = await db.get(Candidate, str(lead.candidate_id))
        if (
            existing is not None
            and str(existing.tenant_id) == str(tenant_id)
            and existing.deleted_at is None
        ):
            return existing
    cand = await find_compliance_shell_candidate_for_lead(
        db, tenant_id=tenant_id, lead=lead
    )
    if cand is None:
        return None
    lead.candidate_id = str(cand.id)
    # Clear shell-only marker once Process attaches (optional; keep audit trail).
    extra = _record(getattr(cand, "extra", None))
    if extra.get(SHELL_EXTRA_KEY) is True:
        extra["compliance_shell_attached_at_process"] = datetime.now(timezone.utc).isoformat()
        cand.extra = extra
        flag_modified(cand, "extra")
    await db.flush()
    return cand


async def ensure_candidate_shell_and_application_for_compliance_outbound(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    source: str = "compliance_outbound",
    force_pool_intent: bool = False,
) -> ComplianceOutboundEnsureResult:
    """Idempotent Candidate shell + Application when ADR-031 §2.4 conditions hold.

    Raises ``ComplianceOutboundEnsureError`` / ``ApplicationTransportConflictError``
    when destination/intent forbids creation. Does **not** set ``lead.candidate_id``.
    """
    tid = str(tenant_id).strip()
    lid = str(getattr(lead, "id", "") or "").strip()
    if not tid or not lid:
        raise ComplianceOutboundEnsureError(
            "tenant_id and lead.id are required",
            details={"reason": "missing_ids"},
        )

    if str(getattr(lead, "status", "") or "") == "duplicate_review":
        raise ComplianceOutboundEnsureError(
            "Application ensure blocked while Lead is in duplicate_review",
            details={"lead_id": lid, "reason": "duplicate_review"},
        )

    if lead_is_sales_bound_for_recruitment_ensure(lead):
        raise ApplicationTransportConflictError(
            "transport lead is Sales-bound; Recruitment compliance ensure unavailable",
            details={"lead_id": lid, "reason": "sales_bound"},
        )

    if not lead_is_recruitment_destination_for_compliance(lead):
        raise ComplianceOutboundEnsureError(
            "transport lead is not a Recruitment destination for compliance outbound",
            details={"lead_id": lid, "reason": "not_recruitment_destination"},
        )

    if force_pool_intent and not lead_has_recruitment_intent(lead):
        norm = _record(getattr(lead, "normalized", None))
        norm["recruitment_pool_intent_v1"] = True
        lead.normalized = norm
        flag_modified(lead, "normalized")

    if not lead_has_recruitment_intent(lead):
        raise ComplianceOutboundEnsureError(
            "vacancy_id or explicit pool intent required before Application ensure",
            details={"lead_id": lid, "reason": "missing_recruitment_intent"},
        )

    created_shell = False
    created_application = False

    existing_app = await _application_for_lead(db, tenant_id=tid, lead_id=lid)
    if existing_app is not None:
        app = await ensure_application_result_for_transport_lead(
            db,
            tenant_id=tid,
            lead=lead,
            candidate_id=str(existing_app.candidate_id),
            source=str(source or "compliance_outbound").strip() or "compliance_outbound",
        )
        if app is None:
            raise ComplianceOutboundEnsureError(
                "Recruitment Application ensure returned no row for existing Application",
                details={
                    "lead_id": lid,
                    "application_id": str(existing_app.id),
                    "reason": "application_ensure_failed",
                },
            )
        return ComplianceOutboundEnsureResult(
            candidate_id=str(app.candidate_id),
            application_id=str(app.id),
            created_shell=False,
            created_application=False,
        )

    # Prefer existing lead.candidate_id only if already linked (rare for early path).
    cid = str(getattr(lead, "candidate_id", None) or "").strip()
    candidate: Optional[Candidate] = None
    if cid:
        candidate = await db.get(Candidate, cid)
        if (
            candidate is None
            or str(candidate.tenant_id) != tid
            or candidate.deleted_at is not None
        ):
            candidate = None
            cid = ""

    if candidate is None:
        payload = _candidate_payload_from_lead(lead, source=source)
        # source_lead=None: do not run conversion carry / mark Lead converted.
        candidate = await create_candidate_full(
            db,
            tenant_id=tid,
            payload=payload,
            actor_id=None,
            acl=None,
            source_lead=None,
        )
        created_shell = True
        cid = str(candidate.id)
        # Critical UX: Lead rail stays intake until Process attaches the shell.
        if getattr(lead, "candidate_id", None):
            lead.candidate_id = None
            await db.flush()

    app_before = await _application_for_lead(db, tenant_id=tid, lead_id=lid)
    app = await ensure_application_result_for_transport_lead(
        db,
        tenant_id=tid,
        lead=lead,
        candidate_id=cid,
        source=str(source or "compliance_outbound").strip() or "compliance_outbound",
        meta={
            "compliance_outbound_v1": {
                "shell": True,
                "lead_candidate_id_linked": False,
            }
        },
    )
    if app is None:
        raise ComplianceOutboundEnsureError(
            "Recruitment Application ensure returned no row",
            details={"lead_id": lid, "candidate_id": cid, "reason": "application_ensure_failed"},
        )
    if app_before is None:
        created_application = True

    return ComplianceOutboundEnsureResult(
        candidate_id=cid,
        application_id=str(app.id),
        created_shell=created_shell,
        created_application=created_application,
    )


async def maybe_ensure_compliance_outbound_for_recruitment_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    source: str,
) -> Optional[ComplianceOutboundEnsureResult]:
    """Best-effort ensure when §2.4 destination/intent hold; no-op otherwise.

    Does not raise for non-recruitment / missing intent — callers keep fail-closed send.
    Propagates Sales conflict and duplicate_review errors.
    """
    if str(getattr(lead, "status", "") or "") == "duplicate_review":
        raise ComplianceOutboundEnsureError(
            "Application ensure blocked while Lead is in duplicate_review",
            details={"lead_id": str(lead.id), "reason": "duplicate_review"},
        )
    if lead_is_sales_bound_for_recruitment_ensure(lead):
        return None
    if not lead_is_recruitment_destination_for_compliance(lead):
        return None
    if not lead_has_recruitment_intent(lead):
        return None
    return await ensure_candidate_shell_and_application_for_compliance_outbound(
        db,
        tenant_id=tenant_id,
        lead=lead,
        source=source,
    )
