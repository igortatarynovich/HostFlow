"""ADR-022 Phase 2 — Sales Convert mapping (deterministic, fail-closed).

Contract owner: Sales.
Input: confirmed SalesInquiry + confirmed destination + opaque Flights ledger id.
Output: Sales-owned ClientAccount result + immutable convert mapping + traceability refs.

Does NOT: decide Capability, match, dispatch, create review, change destination,
fallback, or import Recruitment.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.acquisition.flights.destination_registry import DESTINATION_RECRUITMENT, DESTINATION_SALES
from backend.app.models.flight_dispatch_ledger import STATUS_CONFIRMED, FlightDispatchLedger
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.client_accounts import crud as account_crud
from backend.app.modules.client_accounts.conversion import convert_client_lead

CONVERT_MAPPING_KEY = "convert_mapping_v1"
CONVERT_MAPPING_VERSION = 1

# States that may enter convert (including already-converted for idempotent replay).
_CONVERTIBLE_STATUSES = frozenset(
    {
        "received",
        "open",
        "reviewing",
        "waiting_for_information",
        "converted",
    }
)
_TERMINAL_BLOCKED_STATUSES = frozenset({"rejected", "closed", "abandoned"})


class ConvertMappingError(Exception):
    """Fail-closed Convert mapping — no automatic state repair."""

    code = "sales_convert_mapping_error"

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.reason = str(reason)
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class ConvertMappingResult:
    """Immutable convert outcome + lineage refs (no Capability / Review decisions)."""

    client_account_id: str
    sales_inquiry_id: str
    flights_ledger_id: str
    destination: str
    mapping: dict[str, Any]
    company_id: Optional[str]
    idempotent_replay: bool
    traceability_refs: dict[str, Any]


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _trim(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _actor_id_for_company_convert(actor_id: Optional[str]) -> Optional[str]:
    """Company create requires a real user UUID — never invent / pass opaque labels."""
    raw = _trim(actor_id)
    if not raw:
        return None
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        return None


def extract_questionnaire_projections(
    *,
    inquiry: SalesInquiry,
    lead_normalized: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic field projections for the immutable mapping snapshot."""
    norm = _record(lead_normalized)
    need = _record(norm.get("need"))
    questionnaire = _record(norm.get("sales_questionnaire")) or _record(norm.get("questionnaire"))
    meta = _record(getattr(inquiry, "meta", None))

    industry = (
        _trim(need.get("industry"))
        or _trim(questionnaire.get("industry"))
        or _trim(norm.get("industry"))
    )
    budget = (
        _trim(need.get("budget"))
        or _trim(questionnaire.get("budget"))
        or _trim(norm.get("budget"))
    )
    timeline = (
        _trim(need.get("timeline"))
        or _trim(questionnaire.get("timeline"))
        or _trim(norm.get("timeline"))
    )
    notes = (
        _trim(need.get("notes"))
        or _trim(questionnaire.get("notes"))
        or _trim(norm.get("notes"))
        or _trim(getattr(inquiry, "notes", None))
    )
    source_form_id = (
        _trim(getattr(inquiry, "form_id", None))
        or _trim(norm.get("source_form_id"))
        or _trim(questionnaire.get("form_id"))
        or _trim(meta.get("source_form_id"))
    )

    out: dict[str, Any] = {}
    if industry:
        out["industry"] = industry
    if budget:
        out["budget"] = budget
    if timeline:
        out["timeline"] = timeline
    if notes:
        out["notes"] = notes
    if source_form_id:
        out["source_form_id"] = source_form_id
    return out


def _build_mapping_snapshot(
    *,
    sales_inquiry_id: str,
    client_account_id: str,
    company_id: Optional[str],
    destination: str,
    flights_ledger_id: str,
    route_intent: str,
    questionnaire_projections: dict[str, Any],
    actor_id: Optional[str],
) -> dict[str, Any]:
    return {
        "version": CONVERT_MAPPING_VERSION,
        "sales_inquiry_id": sales_inquiry_id,
        "client_account_id": client_account_id,
        "company_id": company_id,
        "destination": destination,
        "flights_ledger_id": flights_ledger_id,
        "route_intent": route_intent,
        "questionnaire_projections": dict(questionnaire_projections),
        "converted_at": datetime.now(timezone.utc).isoformat(),
        "converted_by": actor_id,
    }


def _traceability_refs(
    *,
    sales_inquiry_id: str,
    client_account_id: str,
    flights_ledger_id: str,
    company_id: Optional[str],
) -> dict[str, Any]:
    refs: dict[str, Any] = {
        "sales_inquiry_id": sales_inquiry_id,
        "client_account_id": client_account_id,
        "flights_ledger_id": flights_ledger_id,
    }
    if company_id:
        refs["company_id"] = company_id
    return refs


def _existing_mapping(inquiry: SalesInquiry) -> Optional[dict[str, Any]]:
    meta = _record(getattr(inquiry, "meta", None))
    raw = meta.get(CONVERT_MAPPING_KEY)
    return dict(raw) if isinstance(raw, dict) and raw.get("client_account_id") else None


def _review_blocks_convert(inquiry: SalesInquiry) -> bool:
    status = str(getattr(inquiry, "status", "") or "").strip()
    if status == "review_required":
        return True
    meta = _record(getattr(inquiry, "meta", None))
    if meta.get("review_required") is True and not meta.get("review_confirmed"):
        return True
    return False


def _assert_inquiry_convertible(inquiry: SalesInquiry) -> None:
    status = str(getattr(inquiry, "status", "") or "").strip()
    if status in _TERMINAL_BLOCKED_STATUSES:
        raise ConvertMappingError(
            "SalesInquiry state is not convertible",
            reason="invalid_inquiry_state",
            details={"sales_inquiry_id": str(inquiry.id), "status": status},
        )
    if status not in _CONVERTIBLE_STATUSES and status != "review_required":
        raise ConvertMappingError(
            "SalesInquiry state is not convertible",
            reason="invalid_inquiry_state",
            details={"sales_inquiry_id": str(inquiry.id), "status": status},
        )
    if _review_blocks_convert(inquiry):
        raise ConvertMappingError(
            "SalesInquiry still requires review confirmation",
            reason="unresolved_review",
            details={"sales_inquiry_id": str(inquiry.id), "status": status},
        )


def _assert_destination(destination: str) -> str:
    dest = _trim(destination)
    if not dest:
        raise ConvertMappingError(
            "confirmed destination is required",
            reason="missing_destination",
            details={},
        )
    if dest == DESTINATION_RECRUITMENT or dest in {"recruitment", "candidate_application"}:
        raise ConvertMappingError(
            "Recruitment destination is rejected for Sales convert",
            reason="recruitment_destination_rejected",
            details={"destination": dest},
        )
    if dest != DESTINATION_SALES:
        raise ConvertMappingError(
            "destination must be confirmed Sales destination",
            reason="destination_mismatch",
            details={"destination": dest, "expected": DESTINATION_SALES},
        )
    return dest


async def _load_confirmed_ledger(
    db: AsyncSession,
    *,
    tenant_id: str,
    flights_ledger_id: str,
    sales_inquiry_id: str,
    destination: str,
) -> FlightDispatchLedger:
    lid = _trim(flights_ledger_id)
    if not lid:
        raise ConvertMappingError(
            "opaque Flights reference is required",
            reason="missing_flights_reference",
            details={},
        )
    row = await db.scalar(
        select(FlightDispatchLedger).where(
            FlightDispatchLedger.id == lid,
            FlightDispatchLedger.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise ConvertMappingError(
            "opaque Flights reference not found",
            reason="missing_flights_reference",
            details={"flights_ledger_id": lid},
        )
    if str(row.status or "").strip() != STATUS_CONFIRMED:
        raise ConvertMappingError(
            "Flights provenance is not confirmed",
            reason="unconfirmed_flights_reference",
            details={"flights_ledger_id": lid, "status": row.status},
        )
    ledger_dest = str(row.destination or "").strip()
    if ledger_dest == DESTINATION_RECRUITMENT:
        raise ConvertMappingError(
            "Recruitment destination is rejected for Sales convert",
            reason="recruitment_destination_rejected",
            details={"flights_ledger_id": lid, "destination": ledger_dest},
        )
    if ledger_dest != destination:
        raise ConvertMappingError(
            "Flights ledger destination does not match confirmed destination",
            reason="destination_mismatch",
            details={
                "flights_ledger_id": lid,
                "ledger_destination": ledger_dest,
                "destination": destination,
            },
        )
    result_id = str(row.result_id or "").strip()
    if result_id and result_id != sales_inquiry_id:
        raise ConvertMappingError(
            "Flights opaque result does not match SalesInquiry",
            reason="provenance_mismatch",
            details={
                "flights_ledger_id": lid,
                "result_id": result_id,
                "sales_inquiry_id": sales_inquiry_id,
            },
        )
    return row


def _stamp_immutable_mapping(inquiry: SalesInquiry, mapping: dict[str, Any]) -> None:
    meta = _record(getattr(inquiry, "meta", None))
    existing = meta.get(CONVERT_MAPPING_KEY)
    if isinstance(existing, dict) and existing.get("client_account_id"):
        # Never rewrite an established mapping.
        return
    meta[CONVERT_MAPPING_KEY] = dict(mapping)
    inquiry.meta = meta
    flag_modified(inquiry, "meta")
    inquiry.status = "converted"


def _merge_projections_into_lead_normalized(lead: Any, projections: dict[str, Any]) -> None:
    """Carry questionnaire projections into transport Lead for Company.extra (no rematch)."""
    if not projections:
        return
    norm = _record(getattr(lead, "normalized", None))
    need = _record(norm.get("need"))
    for key in ("industry", "budget", "timeline", "notes"):
        value = projections.get(key)
        if value and not need.get(key):
            need[key] = value
    if projections.get("source_form_id") and not norm.get("source_form_id"):
        norm["source_form_id"] = projections["source_form_id"]
    if need:
        norm["need"] = need
    lead.normalized = norm
    flag_modified(lead, "normalized")


async def convert_sales_inquiry_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    sales_inquiry_id: str,
    destination: str,
    flights_ledger_id: str,
    actor_id: Optional[str] = None,
) -> ConvertMappingResult:
    """Deterministic Sales convert — fail-closed; idempotent on replay."""
    tid = _trim(tenant_id)
    sid = _trim(sales_inquiry_id)
    if not tid or not sid:
        raise ConvertMappingError(
            "tenant_id and sales_inquiry_id are required",
            reason="invalid_inquiry_state",
            details={"tenant_id": tid, "sales_inquiry_id": sid},
        )

    dest = _assert_destination(destination)

    inquiry = await db.scalar(
        select(SalesInquiry)
        .where(SalesInquiry.id == sid, SalesInquiry.tenant_id == tid)
        .with_for_update()
    )
    if inquiry is None:
        raise ConvertMappingError(
            "SalesInquiry not found",
            reason="invalid_inquiry_state",
            details={"sales_inquiry_id": sid},
        )

    existing = _existing_mapping(inquiry)
    if existing is not None:
        # Idempotent replay — do not re-validate review/destination changes into a new mapping.
        return ConvertMappingResult(
            client_account_id=str(existing["client_account_id"]),
            sales_inquiry_id=sid,
            flights_ledger_id=str(existing.get("flights_ledger_id") or flights_ledger_id),
            destination=str(existing.get("destination") or dest),
            mapping=dict(existing),
            company_id=_trim(existing.get("company_id")),
            idempotent_replay=True,
            traceability_refs=_traceability_refs(
                sales_inquiry_id=sid,
                client_account_id=str(existing["client_account_id"]),
                flights_ledger_id=str(existing.get("flights_ledger_id") or flights_ledger_id),
                company_id=_trim(existing.get("company_id")),
            ),
        )

    _assert_inquiry_convertible(inquiry)

    ledger = await _load_confirmed_ledger(
        db,
        tenant_id=tid,
        flights_ledger_id=flights_ledger_id,
        sales_inquiry_id=sid,
        destination=dest,
    )
    ledger_id = str(ledger.id)
    route_intent = str(ledger.route_intent or "sales_inquiry").strip() or "sales_inquiry"

    lead_id = _trim(getattr(inquiry, "lead_id", None))
    if not lead_id:
        raise ConvertMappingError(
            "SalesInquiry lacks transport lead for convert mapping",
            reason="invalid_inquiry_state",
            details={"sales_inquiry_id": sid},
        )

    lead = await account_crud.get_lead_for_update(db, tenant_id=tid, lead_id=lead_id)
    if lead is None:
        raise ConvertMappingError(
            "SalesInquiry transport lead not found",
            reason="invalid_inquiry_state",
            details={"sales_inquiry_id": sid, "lead_id": lead_id},
        )

    projections = extract_questionnaire_projections(
        inquiry=inquiry,
        lead_normalized=_record(getattr(lead, "normalized", None)),
    )
    _merge_projections_into_lead_normalized(lead, projections)

    conversion = await convert_client_lead(
        db,
        tenant_id=tid,
        lead=lead,
        actor_id=_actor_id_for_company_convert(actor_id),
        conversion_reason="sales_inquiry_convert_mapping",
    )
    account_id = str(conversion.client_account.id)
    company_id = str(conversion.company.id) if conversion.company is not None else None

    mapping = _build_mapping_snapshot(
        sales_inquiry_id=sid,
        client_account_id=account_id,
        company_id=company_id,
        destination=dest,
        flights_ledger_id=ledger_id,
        route_intent=route_intent,
        questionnaire_projections=projections,
        actor_id=actor_id,
    )
    _stamp_immutable_mapping(inquiry, mapping)
    await db.flush()

    # Re-read to guarantee immutability of what callers observe.
    stamped = _existing_mapping(inquiry) or mapping

    return ConvertMappingResult(
        client_account_id=account_id,
        sales_inquiry_id=sid,
        flights_ledger_id=ledger_id,
        destination=dest,
        mapping=dict(stamped),
        company_id=company_id,
        idempotent_replay=bool(conversion.idempotent_replay),
        traceability_refs=_traceability_refs(
            sales_inquiry_id=sid,
            client_account_id=account_id,
            flights_ledger_id=ledger_id,
            company_id=company_id,
        ),
    )
