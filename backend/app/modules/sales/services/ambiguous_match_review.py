"""ADR-022 Phase 2 — SalesInquiry-owned ambiguous match review.

SoT: SalesInquiry.meta[ambiguous_match_review_v1]
Owner: Sales. Flights supplies provenance/destination context only.
Does NOT: own UI, Capability, Flights destination, Recruitment review, or shared review engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.acquisition.flights.destination_registry import DESTINATION_RECRUITMENT, DESTINATION_SALES
from backend.app.models.client_account import ClientAccount
from backend.app.models.flight_dispatch_ledger import STATUS_CONFIRMED, FlightDispatchLedger
from backend.app.models.sales_inquiry import SalesInquiry

REVIEW_KEY = "ambiguous_match_review_v1"
REVIEW_VERSION = 1

STATUS_NOT_REQUIRED = "not_required"
STATUS_REQUIRED = "required"
STATUS_RESOLVED_MATCH = "resolved_match"
STATUS_RESOLVED_CREATE_NEW = "resolved_create_new"
STATUS_CANCELLED = "cancelled"

DECISION_MATCH_EXISTING = "match_existing"
DECISION_CREATE_NEW = "create_new"

_RESOLVED_STATUSES = frozenset({STATUS_RESOLVED_MATCH, STATUS_RESOLVED_CREATE_NEW})
_SALES_REVIEW_ROLES = frozenset(
    {
        "admin",
        "administrator",
        "manager",
        "supervisor",
    }
)


class AmbiguousMatchReviewError(Exception):
    """Fail-closed SalesInquiry review — no automatic repair."""

    code = "sales_ambiguous_match_review_error"

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
class AmbiguityCandidateRef:
    """Opaque Sales-scoped candidate — ClientAccount id only."""

    client_account_id: str
    label: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    action: str  # match_existing | create_new
    client_account_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class AmbiguousMatchReviewResult:
    sales_inquiry_id: str
    status: str
    version: int
    review: dict[str, Any]
    convert_ready_ref: dict[str, Any]
    idempotent_replay: bool


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _trim(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _audit_entry(
    *,
    event: str,
    actor_id: Optional[str],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event": event,
        "actor_id": actor_id,
        "at": _now(),
        "payload": dict(payload or {}),
    }


def read_review_state(inquiry: SalesInquiry) -> Optional[dict[str, Any]]:
    meta = _record(getattr(inquiry, "meta", None))
    raw = meta.get(REVIEW_KEY)
    return dict(raw) if isinstance(raw, dict) else None


def review_blocks_convert(inquiry: SalesInquiry) -> bool:
    """Convert gate: block while review status is required (SoT = review block)."""
    state = read_review_state(inquiry)
    if state is not None:
        return str(state.get("status") or "").strip() == STATUS_REQUIRED
    # Legacy bridge used by Convert mapping slice 2 tests / stamps.
    status = str(getattr(inquiry, "status", "") or "").strip()
    if status == "review_required":
        return True
    meta = _record(getattr(inquiry, "meta", None))
    return bool(meta.get("review_required") is True and not meta.get("review_confirmed"))


def _write_review(inquiry: SalesInquiry, review: dict[str, Any]) -> None:
    meta = _record(getattr(inquiry, "meta", None))
    meta[REVIEW_KEY] = dict(review)
    status = str(review.get("status") or "").strip()
    if status == STATUS_REQUIRED:
        meta["review_required"] = True
        meta.pop("review_confirmed", None)
        inquiry.status = "review_required"
    elif status in _RESOLVED_STATUSES:
        meta["review_required"] = False
        meta["review_confirmed"] = True
        if str(getattr(inquiry, "status", "") or "").strip() == "review_required":
            inquiry.status = "open"
    elif status == STATUS_NOT_REQUIRED:
        meta["review_required"] = False
        meta["review_confirmed"] = True
    elif status == STATUS_CANCELLED:
        meta["review_required"] = False
    inquiry.meta = meta
    flag_modified(inquiry, "meta")


def _assert_sales_actor(*, actor_id: Optional[str], actor_role: Optional[str]) -> str:
    aid = _trim(actor_id)
    if not aid:
        raise AmbiguousMatchReviewError(
            "Sales actor is required",
            reason="actor_permission_denied",
            details={},
        )
    role = str(actor_role or "").strip().lower()
    if role not in _SALES_REVIEW_ROLES:
        raise AmbiguousMatchReviewError(
            "actor lacks Sales review permission",
            reason="actor_permission_denied",
            details={"actor_id": aid, "actor_role": role},
        )
    return aid


def _normalize_candidates(
    candidates: Sequence[AmbiguityCandidateRef | dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in candidates:
        if isinstance(raw, AmbiguityCandidateRef):
            cid = _trim(raw.client_account_id)
            label = _trim(raw.label)
            kind = "client_account"
        else:
            row = _record(raw)
            kind = _trim(row.get("kind") or row.get("result_type")) or "client_account"
            if kind in {"application", "candidate", "recruitment", "recruitment_application"}:
                raise AmbiguousMatchReviewError(
                    "Recruitment results cannot enter Sales ambiguity evidence",
                    reason="recruitment_result_rejected",
                    details={"kind": kind},
                )
            cid = _trim(row.get("client_account_id") or row.get("id") or row.get("result_id"))
            label = _trim(row.get("label"))
        if not cid:
            raise AmbiguousMatchReviewError(
                "ambiguity candidate missing client_account_id",
                reason="invalid_candidate",
                details={},
            )
        if cid in seen:
            continue
        seen.add(cid)
        item: dict[str, Any] = {"client_account_id": cid, "kind": "client_account"}
        if label:
            item["label"] = label
        out.append(item)
    return out


def _candidate_ids(review: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for row in review.get("candidates") or []:
        if isinstance(row, dict):
            cid = _trim(row.get("client_account_id"))
            if cid:
                ids.add(cid)
    return ids


def _convert_ready_ref(inquiry_id: str, review: dict[str, Any]) -> dict[str, Any]:
    return {
        "sales_inquiry_id": inquiry_id,
        "review_status": review.get("status"),
        "review_version": review.get("version"),
        "decision": dict(review.get("decision") or {}) if isinstance(review.get("decision"), dict) else None,
        "flights_ledger_id": review.get("flights_ledger_id"),
        "destination": review.get("destination"),
        "convert_allowed": str(review.get("status") or "") in {
            STATUS_NOT_REQUIRED,
            STATUS_RESOLVED_MATCH,
            STATUS_RESOLVED_CREATE_NEW,
        },
    }


async def _load_inquiry(
    db: AsyncSession,
    *,
    tenant_id: str,
    sales_inquiry_id: str,
    own_company_id: Optional[str] = None,
) -> SalesInquiry:
    tid = _trim(tenant_id)
    sid = _trim(sales_inquiry_id)
    if not tid or not sid:
        raise AmbiguousMatchReviewError(
            "tenant_id and sales_inquiry_id are required",
            reason="invalid_inquiry_state",
            details={},
        )
    inquiry = await db.scalar(
        select(SalesInquiry)
        .where(SalesInquiry.id == sid, SalesInquiry.tenant_id == tid)
        .with_for_update()
    )
    if inquiry is None:
        raise AmbiguousMatchReviewError(
            "SalesInquiry not found",
            reason="invalid_inquiry_state",
            details={"sales_inquiry_id": sid},
        )
    expected_oc = _trim(own_company_id)
    if expected_oc:
        actual_oc = _trim(getattr(inquiry, "own_company_id", None))
        if actual_oc and actual_oc != expected_oc:
            raise AmbiguousMatchReviewError(
                "SalesInquiry own_company mismatch",
                reason="invalid_inquiry_state",
                details={
                    "sales_inquiry_id": sid,
                    "own_company_id": actual_oc,
                    "expected_own_company_id": expected_oc,
                },
            )
    status = str(getattr(inquiry, "status", "") or "").strip()
    if status in {"rejected", "closed", "abandoned"}:
        raise AmbiguousMatchReviewError(
            "SalesInquiry state does not allow review",
            reason="invalid_inquiry_state",
            details={"sales_inquiry_id": sid, "status": status},
        )
    return inquiry


async def _assert_confirmed_sales_provenance(
    db: AsyncSession,
    *,
    tenant_id: str,
    sales_inquiry_id: str,
    destination: str,
    flights_ledger_id: str,
) -> FlightDispatchLedger:
    dest = _trim(destination)
    if not dest:
        raise AmbiguousMatchReviewError(
            "confirmed destination is required",
            reason="missing_destination",
            details={},
        )
    if dest == DESTINATION_RECRUITMENT or dest in {"recruitment", "candidate_application"}:
        raise AmbiguousMatchReviewError(
            "Recruitment destination rejected for Sales review",
            reason="recruitment_destination_rejected",
            details={"destination": dest},
        )
    if dest != DESTINATION_SALES:
        raise AmbiguousMatchReviewError(
            "destination must be confirmed Sales",
            reason="destination_mismatch",
            details={"destination": dest, "expected": DESTINATION_SALES},
        )

    lid = _trim(flights_ledger_id)
    if not lid:
        raise AmbiguousMatchReviewError(
            "opaque Flights provenance is required",
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
        raise AmbiguousMatchReviewError(
            "Flights provenance not found",
            reason="missing_flights_reference",
            details={"flights_ledger_id": lid},
        )
    if str(row.status or "").strip() != STATUS_CONFIRMED:
        raise AmbiguousMatchReviewError(
            "Flights provenance is not confirmed",
            reason="unconfirmed_flights_reference",
            details={"flights_ledger_id": lid, "status": row.status},
        )
    ledger_dest = str(row.destination or "").strip()
    if ledger_dest == DESTINATION_RECRUITMENT:
        raise AmbiguousMatchReviewError(
            "Recruitment destination rejected for Sales review",
            reason="recruitment_destination_rejected",
            details={"flights_ledger_id": lid, "destination": ledger_dest},
        )
    if ledger_dest != dest:
        raise AmbiguousMatchReviewError(
            "Flights ledger destination mismatch",
            reason="destination_mismatch",
            details={
                "flights_ledger_id": lid,
                "ledger_destination": ledger_dest,
                "destination": dest,
            },
        )
    result_id = str(row.result_id or "").strip()
    if result_id and result_id != sales_inquiry_id:
        raise AmbiguousMatchReviewError(
            "Flights provenance does not match SalesInquiry",
            reason="provenance_mismatch",
            details={
                "flights_ledger_id": lid,
                "result_id": result_id,
                "sales_inquiry_id": sales_inquiry_id,
            },
        )
    return row


async def _assert_client_account_in_scope(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str],
    client_account_id: str,
    allowed_ids: set[str],
) -> ClientAccount:
    cid = _trim(client_account_id)
    if not cid:
        raise AmbiguousMatchReviewError(
            "client_account_id is required",
            reason="invalid_candidate",
            details={},
        )
    if cid not in allowed_ids:
        raise AmbiguousMatchReviewError(
            "selected ClientAccount is outside ambiguity evidence",
            reason="candidate_outside_evidence",
            details={"client_account_id": cid},
        )
    account = await db.scalar(
        select(ClientAccount).where(
            ClientAccount.id == cid,
            ClientAccount.tenant_id == tenant_id,
        )
    )
    if account is None:
        # Missing in tenant → treat as cross-tenant / out of scope.
        foreign = await db.get(ClientAccount, cid)
        if foreign is not None and str(foreign.tenant_id) != tenant_id:
            raise AmbiguousMatchReviewError(
                "ClientAccount belongs to another tenant",
                reason="cross_tenant_candidate",
                details={"client_account_id": cid},
            )
        raise AmbiguousMatchReviewError(
            "ClientAccount not found in tenant scope",
            reason="cross_tenant_candidate",
            details={"client_account_id": cid},
        )
    oc = _trim(own_company_id)
    account_oc = _trim(getattr(account, "own_company_id", None))
    if oc and account_oc and account_oc != oc:
        raise AmbiguousMatchReviewError(
            "ClientAccount own_company outside inquiry scope",
            reason="cross_tenant_candidate",
            details={
                "client_account_id": cid,
                "account_own_company_id": account_oc,
                "inquiry_own_company_id": oc,
            },
        )
    return account


async def open_ambiguous_match_review(
    db: AsyncSession,
    *,
    tenant_id: str,
    sales_inquiry_id: str,
    destination: str,
    flights_ledger_id: str,
    candidates: Sequence[AmbiguityCandidateRef | dict[str, Any]],
    reason: str = "ambiguous_match",
    own_company_id: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> AmbiguousMatchReviewResult:
    """Ambiguity → required. Unique/empty candidate sets must not call this."""
    inquiry = await _load_inquiry(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=sales_inquiry_id,
        own_company_id=own_company_id,
    )
    sid = str(inquiry.id)
    existing = read_review_state(inquiry)
    if existing and str(existing.get("status")) == STATUS_REQUIRED:
        # Idempotent reopen with same evidence fingerprint is allowed as replay.
        return AmbiguousMatchReviewResult(
            sales_inquiry_id=sid,
            status=STATUS_REQUIRED,
            version=int(existing.get("version") or 1),
            review=dict(existing),
            convert_ready_ref=_convert_ready_ref(sid, existing),
            idempotent_replay=True,
        )
    if existing and str(existing.get("status")) in _RESOLVED_STATUSES:
        raise AmbiguousMatchReviewError(
            "resolved review is immutable without reopen flow",
            reason="resolved_immutable",
            details={"sales_inquiry_id": sid, "status": existing.get("status")},
        )

    normalized = _normalize_candidates(candidates)
    if len(normalized) < 2:
        raise AmbiguousMatchReviewError(
            "ambiguity evidence requires multiple candidates",
            reason="invalid_candidate",
            details={"candidate_count": len(normalized)},
        )

    ledger = await _assert_confirmed_sales_provenance(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=sid,
        destination=destination,
        flights_ledger_id=flights_ledger_id,
    )

    # Validate every candidate is in tenant/company scope up front (fail-closed).
    allowed = {str(c["client_account_id"]) for c in normalized}
    for cid in sorted(allowed):
        await _assert_client_account_in_scope(
            db,
            tenant_id=tenant_id,
            own_company_id=_trim(own_company_id) or _trim(getattr(inquiry, "own_company_id", None)),
            client_account_id=cid,
            allowed_ids=allowed,
        )

    review = {
        "version_schema": REVIEW_VERSION,
        "status": STATUS_REQUIRED,
        "reason": _trim(reason) or "ambiguous_match",
        "candidates": normalized,
        "decision": None,
        "version": 1,
        "flights_ledger_id": str(ledger.id),
        "destination": DESTINATION_SALES,
        "created_at": _now(),
        "updated_at": _now(),
        "created_by": _trim(actor_id),
        "resolved_at": None,
        "resolved_by": None,
        "audit": [
            _audit_entry(
                event="review_required",
                actor_id=_trim(actor_id),
                payload={"candidate_count": len(normalized), "reason": _trim(reason) or "ambiguous_match"},
            )
        ],
    }
    _write_review(inquiry, review)
    await db.flush()
    return AmbiguousMatchReviewResult(
        sales_inquiry_id=sid,
        status=STATUS_REQUIRED,
        version=1,
        review=dict(review),
        convert_ready_ref=_convert_ready_ref(sid, review),
        idempotent_replay=False,
    )


async def mark_unique_match_not_required(
    db: AsyncSession,
    *,
    tenant_id: str,
    sales_inquiry_id: str,
    destination: str,
    flights_ledger_id: str,
    matched_client_account_id: Optional[str] = None,
    own_company_id: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> AmbiguousMatchReviewResult:
    """Unique strong match → not_required (explicitly no review)."""
    inquiry = await _load_inquiry(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=sales_inquiry_id,
        own_company_id=own_company_id,
    )
    sid = str(inquiry.id)
    existing = read_review_state(inquiry)
    if existing and str(existing.get("status")) == STATUS_NOT_REQUIRED:
        return AmbiguousMatchReviewResult(
            sales_inquiry_id=sid,
            status=STATUS_NOT_REQUIRED,
            version=int(existing.get("version") or 1),
            review=dict(existing),
            convert_ready_ref=_convert_ready_ref(sid, existing),
            idempotent_replay=True,
        )
    if existing and str(existing.get("status")) == STATUS_REQUIRED:
        raise AmbiguousMatchReviewError(
            "cannot mark not_required while review is required",
            reason="review_still_required",
            details={"sales_inquiry_id": sid},
        )
    if existing and str(existing.get("status")) in _RESOLVED_STATUSES:
        raise AmbiguousMatchReviewError(
            "resolved review is immutable without reopen flow",
            reason="resolved_immutable",
            details={"sales_inquiry_id": sid},
        )

    ledger = await _assert_confirmed_sales_provenance(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=sid,
        destination=destination,
        flights_ledger_id=flights_ledger_id,
    )
    decision = None
    mid = _trim(matched_client_account_id)
    if mid:
        decision = {
            "action": DECISION_MATCH_EXISTING,
            "client_account_id": mid,
            "auto": True,
        }

    review = {
        "version_schema": REVIEW_VERSION,
        "status": STATUS_NOT_REQUIRED,
        "reason": "unique_match",
        "candidates": [{"client_account_id": mid, "kind": "client_account"}] if mid else [],
        "decision": decision,
        "version": 1,
        "flights_ledger_id": str(ledger.id),
        "destination": DESTINATION_SALES,
        "created_at": _now(),
        "updated_at": _now(),
        "created_by": _trim(actor_id),
        "resolved_at": _now(),
        "resolved_by": _trim(actor_id),
        "audit": [
            _audit_entry(
                event="review_not_required",
                actor_id=_trim(actor_id),
                payload={"matched_client_account_id": mid},
            )
        ],
    }
    _write_review(inquiry, review)
    await db.flush()
    return AmbiguousMatchReviewResult(
        sales_inquiry_id=sid,
        status=STATUS_NOT_REQUIRED,
        version=1,
        review=dict(review),
        convert_ready_ref=_convert_ready_ref(sid, review),
        idempotent_replay=False,
    )


async def resolve_ambiguous_match_review(
    db: AsyncSession,
    *,
    tenant_id: str,
    sales_inquiry_id: str,
    destination: str,
    flights_ledger_id: str,
    decision: ReviewDecision | dict[str, Any],
    expected_version: int,
    actor_id: str,
    actor_role: str,
    own_company_id: Optional[str] = None,
) -> AmbiguousMatchReviewResult:
    """Apply Sales decision to required review — fail-closed on conflicts/stale version."""
    actor = _assert_sales_actor(actor_id=actor_id, actor_role=actor_role)
    inquiry = await _load_inquiry(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=sales_inquiry_id,
        own_company_id=own_company_id,
    )
    sid = str(inquiry.id)
    existing = read_review_state(inquiry)
    if existing is None or str(existing.get("status")) != STATUS_REQUIRED:
        if existing and str(existing.get("status")) in _RESOLVED_STATUSES:
            # Idempotent same decision / conflicting decision handled below.
            pass
        elif existing is None:
            raise AmbiguousMatchReviewError(
                "review is not required on this SalesInquiry",
                reason="review_not_required",
                details={"sales_inquiry_id": sid},
            )

    await _assert_confirmed_sales_provenance(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=sid,
        destination=destination,
        flights_ledger_id=flights_ledger_id,
    )

    if isinstance(decision, ReviewDecision):
        action = _trim(decision.action)
        selected_id = _trim(decision.client_account_id)
    else:
        row = _record(decision)
        action = _trim(row.get("action"))
        selected_id = _trim(row.get("client_account_id"))

    if action not in {DECISION_MATCH_EXISTING, DECISION_CREATE_NEW}:
        raise AmbiguousMatchReviewError(
            "unsupported review decision",
            reason="invalid_decision",
            details={"action": action},
        )

    new_decision: dict[str, Any] = {"action": action}
    if action == DECISION_MATCH_EXISTING:
        if not selected_id:
            raise AmbiguousMatchReviewError(
                "match_existing requires client_account_id",
                reason="invalid_decision",
                details={},
            )
        new_decision["client_account_id"] = selected_id
    else:
        new_decision["client_account_id"] = None

    if existing and str(existing.get("status")) in _RESOLVED_STATUSES:
        prev = _record(existing.get("decision"))
        if prev == new_decision or (
            prev.get("action") == new_decision.get("action")
            and prev.get("client_account_id") == new_decision.get("client_account_id")
        ):
            return AmbiguousMatchReviewResult(
                sales_inquiry_id=sid,
                status=str(existing.get("status")),
                version=int(existing.get("version") or 1),
                review=dict(existing),
                convert_ready_ref=_convert_ready_ref(sid, existing),
                idempotent_replay=True,
            )
        raise AmbiguousMatchReviewError(
            "conflicting decision against resolved review",
            reason="conflicting_decision",
            details={
                "sales_inquiry_id": sid,
                "existing_decision": prev,
                "new_decision": new_decision,
            },
        )

    if existing is None or str(existing.get("status")) != STATUS_REQUIRED:
        raise AmbiguousMatchReviewError(
            "review must be required before resolve",
            reason="review_not_required",
            details={"sales_inquiry_id": sid, "status": (existing or {}).get("status")},
        )

    current_version = int(existing.get("version") or 1)
    if int(expected_version) != current_version:
        raise AmbiguousMatchReviewError(
            "stale review version",
            reason="stale_version",
            details={
                "sales_inquiry_id": sid,
                "expected_version": expected_version,
                "current_version": current_version,
            },
        )

    # Provenance on the review record must match the call (no destination rewrite).
    if _trim(existing.get("flights_ledger_id")) != _trim(flights_ledger_id):
        raise AmbiguousMatchReviewError(
            "Flights provenance mismatch for review",
            reason="provenance_mismatch",
            details={
                "review_flights_ledger_id": existing.get("flights_ledger_id"),
                "flights_ledger_id": flights_ledger_id,
            },
        )
    if _trim(existing.get("destination")) not in {None, DESTINATION_SALES}:
        raise AmbiguousMatchReviewError(
            "review destination is not Sales",
            reason="destination_mismatch",
            details={"destination": existing.get("destination")},
        )

    if action == DECISION_MATCH_EXISTING:
        await _assert_client_account_in_scope(
            db,
            tenant_id=tenant_id,
            own_company_id=_trim(own_company_id) or _trim(getattr(inquiry, "own_company_id", None)),
            client_account_id=str(selected_id),
            allowed_ids=_candidate_ids(existing),
        )
        new_status = STATUS_RESOLVED_MATCH
    else:
        new_status = STATUS_RESOLVED_CREATE_NEW

    audit = list(existing.get("audit") or [])
    audit.append(
        _audit_entry(
            event="review_resolved",
            actor_id=actor,
            payload={"decision": new_decision, "from_version": current_version},
        )
    )
    updated = dict(existing)
    updated.update(
        {
            "status": new_status,
            "decision": new_decision,
            "version": current_version + 1,
            "updated_at": _now(),
            "resolved_at": _now(),
            "resolved_by": actor,
            "audit": audit,
        }
    )
    _write_review(inquiry, updated)
    await db.flush()
    return AmbiguousMatchReviewResult(
        sales_inquiry_id=sid,
        status=new_status,
        version=int(updated["version"]),
        review=dict(updated),
        convert_ready_ref=_convert_ready_ref(sid, updated),
        idempotent_replay=False,
    )
