"""Communication Context Resolver (C2).

Thread Result Link → validated immutable CommunicationContext.

Does NOT: pick templates, send messages, import Recruitment/Sales ORM,
read Lead, use non-SoT intake labels, auto-fix legacy links, or create
result links. Purposes are C3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.domain_registry import (
    CommunicationDomainIncompatibleError,
    CommunicationDomainRegistryError,
    CommunicationDomainUnknownOwnerError,
    CommunicationDomainUnknownTypeError,
    platform_communication_domain_registry,
)
from backend.app.communications.result_link import (
    ThreadResultLinkUnresolvedError,
    ThreadResultLinkView,
    _validate_opaque,
    _view,
)
from backend.app.models.communication_thread_result_link import (
    LINK_STATUS_CONFIRMED,
    CommunicationThreadResultLink,
)
from backend.app.models.flight_dispatch_ledger import (
    STATUS_CONFIRMED,
    FlightDispatchLedger,
)

RESOLVER_VERSION = "communication.context_resolver.v1"
RESOLUTION_RESOLVED = "resolved"


class CommunicationContextResolveError(Exception):
    code = "communication_context_resolve_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class CommunicationContext:
    """Immutable C2 resolution result — no purposes (C3)."""

    thread_id: str
    module_owner: str
    result_type: str
    result_id: str
    communication_domain: str
    resolution_status: str
    result_link_id: str
    provenance_ledger_id: str | None
    resolved_at: datetime
    resolver_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "module_owner": self.module_owner,
            "result_type": self.result_type,
            "result_id": self.result_id,
            "communication_domain": self.communication_domain,
            "resolution_status": self.resolution_status,
            "result_link_id": self.result_link_id,
            "provenance_ledger_id": self.provenance_ledger_id,
            "resolved_at": self.resolved_at.isoformat(),
            "resolver_version": self.resolver_version,
        }


def _reject_legacy_kwargs(**kwargs: Any) -> None:
    forbidden = (
        "lead",
        "lead_id",
        "application_kind",
        "form_purpose",
        "FormPurpose",
        "entity_type",
        "entity_id",
        "linked_candidate_id",
        "lead_type",
        "url",
        "frontend_module",
    )
    present = [k for k in forbidden if k in kwargs and kwargs[k] is not None]
    if present:
        raise CommunicationContextResolveError(
            "legacy entity / Lead signals cannot resolve communication context",
            details={
                "forbidden_fields": present,
                "reason": "legacy_entity_link_forbidden",
            },
        )


async def _list_thread_result_link_rows(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
) -> list[CommunicationThreadResultLink]:
    stmt = select(CommunicationThreadResultLink).where(
        CommunicationThreadResultLink.tenant_id == tenant_id,
        CommunicationThreadResultLink.thread_id == thread_id,
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _assert_ledger_confirmed_if_present(
    db: AsyncSession,
    *,
    tenant_id: str,
    ledger_id: str | None,
) -> None:
    lid = str(ledger_id or "").strip()
    if not lid:
        return
    ledger = await db.get(FlightDispatchLedger, lid)
    if ledger is None or str(ledger.tenant_id) != str(tenant_id):
        raise CommunicationContextResolveError(
            "Flights dispatch provenance not found",
            details={"ledger_id": lid, "reason": "missing_provenance"},
        )
    if str(ledger.status) != STATUS_CONFIRMED:
        raise CommunicationContextResolveError(
            "Flights dispatch provenance is not confirmed",
            details={
                "ledger_id": lid,
                "status": ledger.status,
                "reason": "unconfirmed_provenance",
            },
        )


async def _load_validated_link(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
) -> ThreadResultLinkView:
    rows = await _list_thread_result_link_rows(
        db, tenant_id=tenant_id, thread_id=thread_id
    )
    if not rows:
        raise CommunicationContextResolveError(
            "thread is not linked to a confirmed result object",
            details={"thread_id": thread_id, "reason": "missing_result_link"},
        )
    if len(rows) > 1:
        raise CommunicationContextResolveError(
            "multiple active result links for thread (fail-closed)",
            details={
                "thread_id": thread_id,
                "link_ids": [str(r.id) for r in rows],
                "reason": "multiple_active_result_links",
            },
        )
    row = rows[0]
    status = str(row.status or "").strip()
    if status != LINK_STATUS_CONFIRMED:
        raise CommunicationContextResolveError(
            "thread result link is damaged, archived, or unresolved",
            details={
                "thread_id": thread_id,
                "link_id": str(row.id),
                "status": status,
                "reason": "damaged_or_archived_link",
            },
        )
    view = _view(row)
    try:
        _validate_opaque(view.opaque())
    except ThreadResultLinkUnresolvedError as exc:
        raise CommunicationContextResolveError(
            "opaque result reference incomplete",
            details={
                **dict(exc.details),
                "thread_id": thread_id,
                "reason": "ambiguous_or_missing_result",
            },
        ) from exc
    await _assert_ledger_confirmed_if_present(
        db, tenant_id=tenant_id, ledger_id=view.ledger_id
    )
    return view


async def resolve_communication_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
    **legacy_forbidden: Any,
) -> CommunicationContext:
    """Resolve Thread → OpaqueResultRef → CommunicationContext (C2 only)."""
    _reject_legacy_kwargs(**legacy_forbidden)
    tid = str(thread_id or "").strip()
    if not tid:
        raise CommunicationContextResolveError(
            "thread_id is required",
            details={"reason": "missing_thread_id"},
        )

    link = await _load_validated_link(db, tenant_id=str(tenant_id), thread_id=tid)

    try:
        entry = platform_communication_domain_registry().resolve(
            module_owner=link.module_owner,
            result_type=link.result_type,
        )
    except CommunicationDomainUnknownOwnerError as exc:
        raise CommunicationContextResolveError(
            exc.message,
            details={**dict(exc.details), "thread_id": tid},
        ) from exc
    except CommunicationDomainUnknownTypeError as exc:
        raise CommunicationContextResolveError(
            exc.message,
            details={**dict(exc.details), "thread_id": tid},
        ) from exc
    except CommunicationDomainIncompatibleError as exc:
        raise CommunicationContextResolveError(
            exc.message,
            details={**dict(exc.details), "thread_id": tid},
        ) from exc
    except CommunicationDomainRegistryError as exc:
        raise CommunicationContextResolveError(
            exc.message,
            details={**dict(exc.details), "thread_id": tid},
        ) from exc

    # Never invent Recruitment from missing/unknown — domain comes only from registry.
    if entry.communication_domain == "recruitment" and link.module_owner != "recruitment":
        raise CommunicationContextResolveError(
            "resolved domain does not match module_owner (fail-closed)",
            details={
                "module_owner": link.module_owner,
                "communication_domain": entry.communication_domain,
                "reason": "incompatible_result_type",
            },
        )

    return CommunicationContext(
        thread_id=tid,
        module_owner=entry.module_owner,
        result_type=entry.result_type,
        result_id=link.result_id,
        communication_domain=entry.communication_domain,
        resolution_status=RESOLUTION_RESOLVED,
        result_link_id=link.link_id,
        provenance_ledger_id=link.ledger_id,
        resolved_at=datetime.now(timezone.utc),
        resolver_version=RESOLVER_VERSION,
    )
