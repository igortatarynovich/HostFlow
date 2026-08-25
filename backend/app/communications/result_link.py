"""Thread result link contract (Communication Context C1).

Attaches OpaqueResultRef + optional Flights ledger id to a Thread.
Must not import Recruitment/Sales ORM or domain services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.flights.destination_contract import OpaqueResultRef
from backend.app.models.communication_thread_result_link import (
    LINK_STATUS_CONFIRMED,
    LINK_STATUS_UNRESOLVED,
    CommunicationThreadResultLink,
)
from backend.app.models.flight_dispatch_ledger import (
    STATUS_CONFIRMED,
    FlightDispatchLedger,
)


class ThreadResultLinkError(Exception):
    code = "communication_thread_result_link_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ThreadResultLinkConflictError(ThreadResultLinkError):
    code = "communication_thread_result_link_conflict"


class ThreadResultLinkUnresolvedError(ThreadResultLinkError):
    code = "communication_thread_result_link_unresolved"


@dataclass(frozen=True, slots=True)
class ThreadResultLinkView:
    link_id: str
    thread_id: str
    module_owner: str
    result_type: str
    result_id: str
    ledger_id: str | None
    status: str
    provenance_ref: str | None

    def opaque(self) -> OpaqueResultRef:
        return OpaqueResultRef(
            module_owner=self.module_owner,
            result_type=self.result_type,
            result_id=self.result_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "thread_id": self.thread_id,
            "module_owner": self.module_owner,
            "result_type": self.result_type,
            "result_id": self.result_id,
            "ledger_id": self.ledger_id,
            "status": self.status,
            "provenance_ref": self.provenance_ref,
        }


def _view(row: CommunicationThreadResultLink) -> ThreadResultLinkView:
    return ThreadResultLinkView(
        link_id=str(row.id),
        thread_id=str(row.thread_id),
        module_owner=str(row.module_owner),
        result_type=str(row.result_type),
        result_id=str(row.result_id),
        ledger_id=str(row.ledger_id) if row.ledger_id else None,
        status=str(row.status),
        provenance_ref=str(row.ledger_id) if row.ledger_id else None,
    )


def _validate_opaque(opaque: OpaqueResultRef) -> OpaqueResultRef:
    owner = str(opaque.module_owner or "").strip().lower()
    rtype = str(opaque.result_type or "").strip()
    rid = str(opaque.result_id or "").strip()
    if not owner or not rtype or not rid:
        raise ThreadResultLinkUnresolvedError(
            "opaque result reference incomplete",
            details={
                "module_owner": opaque.module_owner,
                "result_type": opaque.result_type,
                "result_id": opaque.result_id,
                "reason": "ambiguous_or_missing_result",
            },
        )
    if owner not in {"recruitment", "sales"}:
        raise ThreadResultLinkUnresolvedError(
            "unsupported module_owner for thread result link",
            details={"module_owner": owner},
        )
    return OpaqueResultRef(module_owner=owner, result_type=rtype, result_id=rid)


def _new_link_row(**kwargs: Any) -> CommunicationThreadResultLink:
    """Factory hook — tests may replace without configuring full ORM registry."""
    return CommunicationThreadResultLink(**kwargs)


async def get_thread_result_link(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
) -> ThreadResultLinkView | None:
    stmt = select(CommunicationThreadResultLink).where(
        CommunicationThreadResultLink.tenant_id == tenant_id,
        CommunicationThreadResultLink.thread_id == thread_id,
    )
    row = await db.scalar(stmt)
    return _view(row) if row is not None else None


async def require_confirmed_thread_result_link(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
) -> ThreadResultLinkView:
    """Fail-closed: missing / unresolved / incomplete → error (C1 contract for C2)."""
    view = await get_thread_result_link(db, tenant_id=tenant_id, thread_id=thread_id)
    if view is None:
        raise ThreadResultLinkUnresolvedError(
            "thread is not linked to a confirmed result object",
            details={"thread_id": thread_id, "reason": "missing_result_link"},
        )
    if view.status != LINK_STATUS_CONFIRMED:
        raise ThreadResultLinkUnresolvedError(
            "thread result link is not confirmed",
            details={
                "thread_id": thread_id,
                "status": view.status,
                "reason": "unconfirmed_provenance",
            },
        )
    _validate_opaque(view.opaque())
    return view


async def attach_thread_result_link(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
    opaque: OpaqueResultRef,
    ledger_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> ThreadResultLinkView:
    """Attach opaque ref to thread. Idempotent when identical; conflict if incompatible."""
    opaque = _validate_opaque(opaque)
    existing = await get_thread_result_link(db, tenant_id=tenant_id, thread_id=thread_id)
    if existing is not None:
        same = (
            existing.module_owner == opaque.module_owner
            and existing.result_type == opaque.result_type
            and existing.result_id == opaque.result_id
        )
        if not same:
            raise ThreadResultLinkConflictError(
                "thread already linked to an incompatible result reference",
                details={
                    "thread_id": thread_id,
                    "existing": existing.to_dict(),
                    "incoming": {
                        "module_owner": opaque.module_owner,
                        "result_type": opaque.result_type,
                        "result_id": opaque.result_id,
                    },
                    "reason": "incompatible_result_references",
                },
            )
        # Refresh ledger_id if previously missing and now provided.
        if ledger_id and not existing.ledger_id:
            stmt = select(CommunicationThreadResultLink).where(
                CommunicationThreadResultLink.id == existing.link_id
            )
            row = await db.scalar(stmt)
            if row is not None:
                row.ledger_id = str(ledger_id)
                row.status = LINK_STATUS_CONFIRMED
                await db.flush()
                return _view(row)
        return existing

    row = _new_link_row(
        id=str(uuid4()),
        tenant_id=str(tenant_id),
        thread_id=str(thread_id),
        module_owner=opaque.module_owner,
        result_type=opaque.result_type,
        result_id=opaque.result_id,
        ledger_id=str(ledger_id).strip() if ledger_id else None,
        status=LINK_STATUS_CONFIRMED,
        meta={
            "contract": "communication.thread_result_link.v1",
            **(dict(meta) if meta else {}),
        },
    )
    db.add(row)
    await db.flush()
    return _view(row)


async def attach_thread_result_from_confirmed_ledger(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
    ledger_id: str,
) -> ThreadResultLinkView:
    """Copy opaque ref from a **confirmed** Flights ledger row (string ids only)."""
    lid = str(ledger_id or "").strip()
    if not lid:
        raise ThreadResultLinkUnresolvedError(
            "ledger_id is required",
            details={"reason": "missing_provenance"},
        )
    ledger = await db.get(FlightDispatchLedger, lid)
    if ledger is None or str(ledger.tenant_id) != str(tenant_id):
        raise ThreadResultLinkUnresolvedError(
            "Flights dispatch ledger not found",
            details={"ledger_id": lid, "reason": "missing_provenance"},
        )
    if str(ledger.status) != STATUS_CONFIRMED:
        raise ThreadResultLinkUnresolvedError(
            "Flights dispatch provenance is not confirmed",
            details={
                "ledger_id": lid,
                "status": ledger.status,
                "reason": "unconfirmed_provenance",
            },
        )
    owner = str(ledger.module_owner or "").strip()
    rtype = str(ledger.result_type or "").strip()
    rid = str(ledger.result_id or "").strip()
    if not owner or not rtype or not rid:
        raise ThreadResultLinkUnresolvedError(
            "confirmed ledger missing opaque result reference",
            details={
                "ledger_id": lid,
                "reason": "ambiguous_or_missing_result",
            },
        )
    return await attach_thread_result_link(
        db,
        tenant_id=tenant_id,
        thread_id=thread_id,
        opaque=OpaqueResultRef(
            module_owner=owner,
            result_type=rtype,
            result_id=rid,
        ),
        ledger_id=lid,
        meta={"source": "flights.dispatch_ledger"},
    )


async def mark_thread_result_link_unresolved(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
    reason: str,
) -> ThreadResultLinkView | None:
    view = await get_thread_result_link(db, tenant_id=tenant_id, thread_id=thread_id)
    if view is None:
        return None
    stmt = select(CommunicationThreadResultLink).where(
        CommunicationThreadResultLink.id == view.link_id
    )
    row = await db.scalar(stmt)
    if row is None:
        return None
    row.status = LINK_STATUS_UNRESOLVED
    meta = dict(row.meta or {})
    meta["unresolved_reason"] = reason
    row.meta = meta
    await db.flush()
    return _view(row)
