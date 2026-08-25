"""ADR-022 Phase 2 — SalesInquiry immutable lineage (traceability).

Sales-owned audit chain. Flights owns dispatch/provenance rows; Sales records
opaque Flights refs in the lineage. Never rewritten / deleted / dynamically
recomputed. Not a business-rule SoT — convert writes links, it does not search.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.client_account import ClientAccount
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.sales.services.ambiguous_match_review import (
    STATUS_NOT_REQUIRED,
    STATUS_REQUIRED,
    STATUS_RESOLVED_CREATE_NEW,
    STATUS_RESOLVED_MATCH,
    read_review_state,
)

LINEAGE_KEY = "sales_inquiry_lineage_v1"
LINEAGE_VERSION = 1
CONVERT_MAPPING_KEY = "convert_mapping_v1"  # shared key name; avoid import cycle with convert_mapping


class SalesInquiryTraceabilityError(Exception):
    """Fail-closed lineage — no auto-repair."""

    code = "sales_inquiry_traceability_error"

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
class SalesInquiryLineageResult:
    sales_inquiry_id: str
    client_account_id: str
    flights_ledger_id: str
    lineage: dict[str, Any]
    idempotent_replay: bool


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _trim(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def read_lineage(inquiry: SalesInquiry) -> Optional[dict[str, Any]]:
    meta = _record(getattr(inquiry, "meta", None))
    raw = meta.get(LINEAGE_KEY)
    if not isinstance(raw, dict):
        return None
    if not _trim(raw.get("sales_inquiry_id")) or not _trim(raw.get("client_account_id")):
        return None
    return dict(raw)


def _link(kind: str, ref_id: Optional[str], *, prev: Optional[str], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {
        "link": kind,
        "id": ref_id,
        "prev": prev,
    }
    if extra:
        node.update(extra)
    return node


def _chain_ref(kind: str, ref_id: Optional[str]) -> str:
    return f"{kind}:{ref_id or 'none'}"


def _review_snapshot_for_lineage(inquiry: SalesInquiry) -> tuple[Optional[dict[str, Any]], bool]:
    """Return (review_node_extra_or_None, review_was_required).

    not_required → omit review link (absent).
    resolved_* → include decision snapshot.
    required (still open) → fail at stamp time.
    missing review block → treat as not required (absent).
    """
    state = read_review_state(inquiry)
    if state is None:
        return None, False
    status = str(state.get("status") or "").strip()
    if status == STATUS_REQUIRED:
        return None, True  # still required — caller must fail
    if status == STATUS_NOT_REQUIRED or status == "cancelled":
        return None, False
    if status in {STATUS_RESOLVED_MATCH, STATUS_RESOLVED_CREATE_NEW}:
        return {
            "status": status,
            "decision": dict(state.get("decision") or {}) if isinstance(state.get("decision"), dict) else None,
            "version": state.get("version"),
            "reason": state.get("reason"),
        }, True
    # Unknown status — fail-closed at stamp
    return {"status": status}, True


def build_lineage_document(
    *,
    tenant_id: str,
    sales_inquiry_id: str,
    flights_ledger_id: str,
    destination: str,
    convert_mapping: dict[str, Any],
    review_extra: Optional[dict[str, Any]],
    include_review_link: bool,
    actor_id: Optional[str] = None,
) -> dict[str, Any]:
    """Pure builder — no DB. Used by stamp + tests for immutability checks."""
    sid = _trim(sales_inquiry_id)
    lid = _trim(flights_ledger_id)
    account_id = _trim(convert_mapping.get("client_account_id"))
    company_id = _trim(convert_mapping.get("company_id"))
    if not sid or not lid or not account_id:
        raise SalesInquiryTraceabilityError(
            "lineage requires sales_inquiry, flights provenance, and convert mapping",
            reason="incomplete_lineage_inputs",
            details={
                "sales_inquiry_id": sid,
                "flights_ledger_id": lid,
                "client_account_id": account_id,
            },
        )

    chain: list[dict[str, Any]] = []
    prev: Optional[str] = None

    chain.append(_link("sales_inquiry", sid, prev=None))
    prev = _chain_ref("sales_inquiry", sid)

    chain.append(
        _link(
            "flights_dispatch",
            lid,
            prev=prev,
            extra={"destination": _trim(destination) or convert_mapping.get("destination")},
        )
    )
    prev = _chain_ref("flights_dispatch", lid)

    if include_review_link:
        if not review_extra:
            raise SalesInquiryTraceabilityError(
                "review reference required for ambiguity lineage",
                reason="missing_review_reference",
                details={"sales_inquiry_id": sid},
            )
        review_id = f"{sid}:review:v{review_extra.get('version') or 1}"
        chain.append(_link("review_decision", review_id, prev=prev, extra=dict(review_extra)))
        prev = _chain_ref("review_decision", review_id)

    chain.append(
        _link(
            "convert_mapping",
            sid,
            prev=prev,
            extra={
                "client_account_id": account_id,
                "company_id": company_id,
                "mapping_version": convert_mapping.get("version"),
            },
        )
    )
    prev = _chain_ref("convert_mapping", sid)

    chain.append(_link("client_account", account_id, prev=prev, extra={"company_id": company_id}))

    return {
        "version": LINEAGE_VERSION,
        "tenant_id": tenant_id,
        "sales_inquiry_id": sid,
        "flights_ledger_id": lid,
        "destination": _trim(destination) or convert_mapping.get("destination"),
        "client_account_id": account_id,
        "company_id": company_id,
        "review": dict(review_extra) if include_review_link and review_extra else None,
        "convert_mapping": {
            "client_account_id": account_id,
            "company_id": company_id,
            "flights_ledger_id": lid,
            "version": convert_mapping.get("version"),
        },
        "chain": chain,
        "created_at": _now(),
        "created_by": _trim(actor_id),
    }


def _stamp_lineage(inquiry: SalesInquiry, lineage: dict[str, Any]) -> None:
    meta = _record(getattr(inquiry, "meta", None))
    existing = meta.get(LINEAGE_KEY)
    if isinstance(existing, dict) and existing.get("client_account_id"):
        return
    meta[LINEAGE_KEY] = dict(lineage)
    inquiry.meta = meta
    flag_modified(inquiry, "meta")


async def record_lineage_after_convert(
    db: AsyncSession,
    *,
    tenant_id: str,
    inquiry: SalesInquiry,
    convert_mapping: dict[str, Any],
    destination: str,
    flights_ledger_id: str,
    actor_id: Optional[str] = None,
) -> SalesInquiryLineageResult:
    """Write immutable lineage once after convert mapping is stamped. Fail-closed."""
    tid = _trim(tenant_id)
    sid = _trim(getattr(inquiry, "id", None))
    if not tid or not sid:
        raise SalesInquiryTraceabilityError(
            "tenant_id and SalesInquiry are required",
            reason="missing_sales_inquiry",
            details={},
        )
    if str(getattr(inquiry, "tenant_id", "") or "").strip() != tid:
        raise SalesInquiryTraceabilityError(
            "SalesInquiry tenant mismatch",
            reason="cross_tenant",
            details={"sales_inquiry_id": sid, "tenant_id": tid},
        )

    existing = read_lineage(inquiry)
    if existing is not None:
        return SalesInquiryLineageResult(
            sales_inquiry_id=sid,
            client_account_id=str(existing["client_account_id"]),
            flights_ledger_id=str(existing.get("flights_ledger_id") or flights_ledger_id),
            lineage=dict(existing),
            idempotent_replay=True,
        )

    mapping = _record(convert_mapping)
    if not mapping.get("client_account_id"):
        # Prefer stamped SoT on inquiry if caller passed a partial snapshot.
        meta_map = _record(_record(getattr(inquiry, "meta", None)).get(CONVERT_MAPPING_KEY))
        if meta_map.get("client_account_id"):
            mapping = meta_map
    if not mapping.get("client_account_id"):
        raise SalesInquiryTraceabilityError(
            "convert mapping missing — orphan convert cannot create lineage",
            reason="orphan_convert",
            details={"sales_inquiry_id": sid},
        )

    lid = _trim(flights_ledger_id) or _trim(mapping.get("flights_ledger_id"))
    if not lid:
        raise SalesInquiryTraceabilityError(
            "Flights provenance missing for lineage",
            reason="missing_flights_reference",
            details={"sales_inquiry_id": sid},
        )
    map_lid = _trim(mapping.get("flights_ledger_id"))
    if map_lid and map_lid != lid:
        raise SalesInquiryTraceabilityError(
            "Flights provenance mismatch between convert mapping and lineage input",
            reason="provenance_mismatch",
            details={
                "sales_inquiry_id": sid,
                "mapping_flights_ledger_id": map_lid,
                "flights_ledger_id": lid,
            },
        )

    account_id = str(mapping["client_account_id"])
    account = await db.scalar(
        select(ClientAccount).where(
            ClientAccount.id == account_id,
            ClientAccount.tenant_id == tid,
        )
    )
    if account is None:
        foreign = await db.get(ClientAccount, account_id)
        if foreign is not None and str(foreign.tenant_id) != tid:
            raise SalesInquiryTraceabilityError(
                "ClientAccount belongs to another tenant",
                reason="cross_tenant",
                details={"client_account_id": account_id},
            )
        raise SalesInquiryTraceabilityError(
            "ClientAccount not found for lineage",
            reason="orphan_convert",
            details={"client_account_id": account_id},
        )

    review_extra, review_was_required_path = _review_snapshot_for_lineage(inquiry)
    state = read_review_state(inquiry)
    if state and str(state.get("status")) == STATUS_REQUIRED:
        raise SalesInquiryTraceabilityError(
            "cannot stamp lineage while review is still required",
            reason="missing_review_reference",
            details={"sales_inquiry_id": sid},
        )
    include_review = bool(review_extra) and review_was_required_path

    # Ambiguity path must have left a resolved review snapshot.
    if state and str(state.get("status")) in {STATUS_RESOLVED_MATCH, STATUS_RESOLVED_CREATE_NEW}:
        include_review = True
        if not review_extra:
            raise SalesInquiryTraceabilityError(
                "resolved review missing decision snapshot",
                reason="missing_review_reference",
                details={"sales_inquiry_id": sid},
            )

    lineage = build_lineage_document(
        tenant_id=tid,
        sales_inquiry_id=sid,
        flights_ledger_id=lid,
        destination=str(destination or mapping.get("destination") or ""),
        convert_mapping=mapping,
        review_extra=review_extra,
        include_review_link=include_review,
        actor_id=actor_id,
    )
    _stamp_lineage(inquiry, lineage)
    await db.flush()

    stamped = read_lineage(inquiry) or lineage
    return SalesInquiryLineageResult(
        sales_inquiry_id=sid,
        client_account_id=account_id,
        flights_ledger_id=lid,
        lineage=dict(stamped),
        idempotent_replay=False,
    )


async def get_lineage_for_sales_inquiry(
    db: AsyncSession,
    *,
    tenant_id: str,
    sales_inquiry_id: str,
) -> dict[str, Any]:
    """Read immutable lineage — never recomputed."""
    tid = _trim(tenant_id)
    sid = _trim(sales_inquiry_id)
    if not tid or not sid:
        raise SalesInquiryTraceabilityError(
            "tenant_id and sales_inquiry_id are required",
            reason="missing_sales_inquiry",
            details={},
        )
    inquiry = await db.scalar(
        select(SalesInquiry).where(SalesInquiry.id == sid, SalesInquiry.tenant_id == tid)
    )
    if inquiry is None:
        raise SalesInquiryTraceabilityError(
            "SalesInquiry not found",
            reason="missing_sales_inquiry",
            details={"sales_inquiry_id": sid},
        )
    lineage = read_lineage(inquiry)
    if lineage is None:
        raise SalesInquiryTraceabilityError(
            "lineage not recorded",
            reason="orphan_trace",
            details={"sales_inquiry_id": sid},
        )
    return dict(lineage)


async def get_lineage_for_client_account(
    db: AsyncSession,
    *,
    tenant_id: str,
    client_account_id: str,
) -> dict[str, Any]:
    """Resolve lineage by ClientAccount via stored SalesInquiry lineage (no dynamic rebuild)."""
    tid = _trim(tenant_id)
    cid = _trim(client_account_id)
    if not tid or not cid:
        raise SalesInquiryTraceabilityError(
            "tenant_id and client_account_id are required",
            reason="orphan_trace",
            details={},
        )
    account = await db.scalar(
        select(ClientAccount).where(ClientAccount.id == cid, ClientAccount.tenant_id == tid)
    )
    if account is None:
        foreign = await db.get(ClientAccount, cid)
        if foreign is not None and str(foreign.tenant_id) != tid:
            raise SalesInquiryTraceabilityError(
                "ClientAccount belongs to another tenant",
                reason="cross_tenant",
                details={"client_account_id": cid},
            )
        raise SalesInquiryTraceabilityError(
            "ClientAccount not found",
            reason="orphan_trace",
            details={"client_account_id": cid},
        )

    # Phase 2: scan converted inquiries in tenant for stamped lineage (immutable record).
    rows = await db.scalars(
        select(SalesInquiry).where(
            SalesInquiry.tenant_id == tid,
            SalesInquiry.status == "converted",
        )
    )
    for inquiry in rows:
        lineage = read_lineage(inquiry)
        if lineage and str(lineage.get("client_account_id")) == cid:
            return dict(lineage)
        mapping = _record(_record(getattr(inquiry, "meta", None)).get(CONVERT_MAPPING_KEY))
        if mapping and str(mapping.get("client_account_id")) == cid and lineage is None:
            raise SalesInquiryTraceabilityError(
                "convert mapping exists without lineage",
                reason="orphan_convert",
                details={"sales_inquiry_id": str(inquiry.id), "client_account_id": cid},
            )

    raise SalesInquiryTraceabilityError(
        "no lineage for ClientAccount",
        reason="orphan_trace",
        details={"client_account_id": cid},
    )


def lineage_has_review(lineage: dict[str, Any]) -> bool:
    if lineage.get("review"):
        return True
    for node in lineage.get("chain") or []:
        if isinstance(node, dict) and node.get("link") == "review_decision":
            return True
    return False
